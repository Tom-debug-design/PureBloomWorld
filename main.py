# main.py
"""
PureBloomWorld Agent v1.1 (Railway-ready, mobile-friendly)

Hva den gjør:
- Startup-ping til Discord
- Heartbeat hver N minutter (ENV: HEARTBEAT_MINUTES)
- /healthz-endpoint
- Serverer forsiden via site_routes.py (router)
- Daglig idé-drop kl. 08:00 Europe/Oslo (3 produkt + 3 artikkel)
- Manuell trigger: GET /trigger/ideas

ENV-vars:
- DISCORD_WEBHOOK   (obligatorisk)
- SERVICE_NAME      (default: purebloomworld-agent)
- ENV               (default: prod)
- HEARTBEAT_MINUTES (default: 60)
"""

import os
import asyncio
import time
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from site_routes import router as site_router
from idea_jobs import daily_ideas_scheduler, compose_idea_message
from gh_push import router as gh_router
app.include_router(gh_router)
# ---------- Config ----------
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")
ENV = os.getenv("ENV", "prod")
HEARTBEAT_MINUTES = int(os.getenv("HEARTBEAT_MINUTES", "60"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

# internal state
STARTED_AT = datetime.now(timezone.utc)
_last_heartbeat_ts = 0.0
_shutdown = asyncio.Event()

app = FastAPI(title="PureBloomWorld Agent", version="1.1.0")
app.include_router(site_router)  # koble inn forsiden

# ---------- Utils ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def post_discord(message: str, username: str = "PBW Agent") -> bool:
    """Send a simple message to Discord webhook. Returns True on success."""
    if not DISCORD_WEBHOOK:
        print("[WARN] DISCORD_WEBHOOK is missing.")
        return False

    payload = {"content": message, "username": username}
    timeout = httpx.Timeout(10.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # tiny retry/backoff: 3 tries (0.5s, 1s)
        for attempt in range(3):
            try:
                r = await client.post(DISCORD_WEBHOOK, json=payload)
                if r.status_code < 300:
                    return True
                else:
                    print(f"[WARN] Discord status {r.status_code}: {r.text}")
            except Exception as e:
                print(f"[WARN] Discord error: {e}")
            await asyncio.sleep(0.5 * (attempt + 1))
    return False


def fmt_startup() -> str:
    return (
        f"✅ **Startup** `{SERVICE_NAME}` ({ENV})\n"
        f"• time: {now_iso()}\n"
        f"• heartbeat: every {HEARTBEAT_MINUTES} min\n"
    )


def fmt_heartbeat() -> str:
    return (
        f"🫀 **Heartbeat** `{SERVICE_NAME}` ({ENV})\n"
        f"• time: {now_iso()}\n"
        f"• uptime_min: {int((time.time()-STARTED_AT.timestamp())/60)}\n"
    )


# ---------- Background tasks ----------
async def heartbeat_loop():
    global _last_heartbeat_ts
    # initial startup ping
    await post_discord(fmt_startup(), username="PBW Agent")
    _last_heartbeat_ts = time.time()

    interval = max(1, HEARTBEAT_MINUTES) * 60
    while not _shutdown.is_set():
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=interval)
        except asyncio.TimeoutError:
            ok = await post_discord(fmt_heartbeat(), username="PBW Agent")
            if ok:
                _last_heartbeat_ts = time.time()


# ---------- FastAPI endpoints ----------
@app.get("/healthz")
async def healthz():
    # healthy if last heartbeat < 2 intervals ago
    interval = max(1, HEARTBEAT_MINUTES) * 60
    age = time.time() - _last_heartbeat_ts if _last_heartbeat_ts else 0
    healthy = True if _last_heartbeat_ts == 0 or age < (2 * interval + 10) else False
    data = {
        "service": SERVICE_NAME,
        "env": ENV,
        "started_at": STARTED_AT.isoformat(timespec="seconds"),
        "last_heartbeat_ts": _last_heartbeat_ts,
        "last_heartbeat_age_sec": int(age),
        "heartbeat_minutes": HEARTBEAT_MINUTES,
        "healthy": healthy,
        "time": now_iso(),
    }
    status = 200 if healthy else 503
    return JSONResponse(data, status_code=status)


@app.get("/trigger/ideas")
async def trigger_ideas():
    """Manuell idé-drop (for testing)."""
    msg = compose_idea_message()
    await post_discord(msg, username="PBW Ideas")
    return Response(content="Ideas sent", media_type="text/plain")


# ---------- Lifespan ----------
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(heartbeat_loop())
    # daglig idé-jobb
    asyncio.create_task(daily_ideas_scheduler(lambda m: post_discord(m, username="PBW Ideas")))
    print(f"[START] {SERVICE_NAME} ({ENV}) at {now_iso()}")


@app.on_event("shutdown")
async def on_shutdown():
    _shutdown.set()
    print(f"[STOP] {SERVICE_NAME} ({ENV}) at {now_iso()}")


# ---------- Local dev (optional) ----------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)