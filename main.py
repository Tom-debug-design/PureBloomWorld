"""
PureBloomWorld Agent – main.py (single-file)

Hva den gjør:
- Startup-ping til Discord
- Heartbeat hver N minutter (ENV: HEARTBEAT_MINUTES)
- /healthz-endpoint
- Serverer forsiden via site_routes.py (router)
- Top-seller loop som kjører periodisk (styrt av ENV)
- Manuell trigger: GET /trigger/topsellers

ENV-vars:
- DISCORD_WEBHOOK     (obligatorisk)
- SERVICE_NAME        (default: purebloomworld-agent)
- ENV                 (default: prod)
- HEARTBEAT_MINUTES   (default: 60)
- TOPSELLER_ENABLE    (default: false)  # "true" for å aktivere
- TOPSELLER_INTERVAL_MIN (default: 60)

Forutsetter:
- `site_routes.py` med `router` definert
- `products.py` med `get_top_sellers(limit:int=10) -> list[dict]`
"""

import os, asyncio, time, json
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

# Routers / helpers fra prosjektet
from site_routes import router as site_router
from products import get_top_sellers  # må finnes i repoet

# ---------- Config ----------
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent").strip()
ENV = os.getenv("ENV", "prod").strip()
HEARTBEAT_MINUTES = int(os.getenv("HEARTBEAT_MINUTES", "60"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

TOPSELLER_ENABLE = os.getenv("TOPSELLER_ENABLE", "false").lower().strip() in {"1", "true", "yes", "on"}
TOPSELLER_INTERVAL_MIN = int(os.getenv("TOPSELLER_INTERVAL_MIN", "60"))

# ---------- Internal state ----------
STARTED_AT = datetime.now(timezone.utc)
_last_heartbeat_ts = 0.0
_shutdown = asyncio.Event()

app = FastAPI(title="PureBloomWorld Agent", version="1.0.0")
app.include_router(site_router)

# ---------- Utils ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def post_discord(msg: str):
    if not DISCORD_WEBHOOK:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(DISCORD_WEBHOOK, json={"content": msg})
    except Exception:
        # Unngå crash pga Discord-problemer
        pass

# ---------- Background tasks ----------
async def heartbeat_loop():
    global _last_heartbeat_ts
    # kjør første heartbeat etter 60s så startup-ping står alene
    await asyncio.sleep(60)
    while not _shutdown.is_set():
        try:
            uptime_min = int((time.time() - STARTED_AT.timestamp()) // 60)
            await post_discord(
                f"🫀 **Heartbeat** `{SERVICE_NAME}` ({ENV})\n"
                f"• time: {now_iso()}\n"
                f"• uptime_min: {uptime_min}"
            )
            _last_heartbeat_ts = time.time()
        except Exception:
            pass

        # søvn
        delay = max(1, HEARTBEAT_MINUTES) * 60
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=delay)
        except asyncio.TimeoutError:
            continue

async def topseller_loop():
    # vent litt etter oppstart
    await asyncio.sleep(5)
    interval = max(5, TOPSELLER_INTERVAL_MIN) * 60  # minst 5 min
    while not _shutdown.is_set():
        try:
            # Hent toppselgere (du kan justere limit)
            items = await get_top_sellers(limit=10)
            # Formater en kort melding (unngå spam)
            lines = []
            for i, it in enumerate(items, start=1):
                title = (it.get("title") or "").strip()
                price = it.get("price")
                src = (it.get("source") or "").strip()
                line = f"{i}. {title[:70]}{'…' if len(title)>70 else ''}"
                if price is not None:
                    line += f" — {price}"
                if src:
                    line += f" [{src}]"
                lines.append(line)
            body = "\n".join(lines[:10]) if lines else "_ingen data_"

            await post_discord(
                f"🛒 **Top Sellers Update** `{SERVICE_NAME}` ({ENV})\n"
                f"• time: {now_iso()}\n"
                f"{body}"
            )
        except Exception as e:
            await post_discord(f"⚠️ TopSeller error: `{type(e).__name__}` — {e}")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue

# ---------- FastAPI events ----------
@app.on_event("startup")
async def startup_event():
    await post_discord(
        f"✅ **Startup** `{SERVICE_NAME}` ({ENV})\n"
        f"• time: {now_iso()}\n"
        f"• heartbeat: every {HEARTBEAT_MINUTES} min\n"
        f"• topseller: {'on' if TOPSELLER_ENABLE else 'off'} / {TOPSELLER_INTERVAL_MIN} min"
    )
    asyncio.create_task(heartbeat_loop())
    if TOPSELLER_ENABLE:
        asyncio.create_task(topseller_loop())

@app.on_event("shutdown")
async def shutdown_event():
    _shutdown.set()
    await post_discord(
        f"🛑 **Shutdown** `{SERVICE_NAME}` ({ENV})\n"
        f"• time: {now_iso()}"
    )

# ---------- Routes ----------
@app.get("/healthz")
async def healthz():
    return JSONResponse(
        {
            "ok": True,
            "service": SERVICE_NAME,
            "env": ENV,
            "started_at": STARTED_AT.isoformat(timespec="seconds"),
            "now": now_iso(),
            "heartbeat_minutes": HEARTBEAT_MINUTES,
            "topseller_enable": TOPSELLER_ENABLE,
            "topseller_interval_min": TOPSELLER_INTERVAL_MIN,
        }
    )

@app.get("/trigger/topsellers")
async def trigger_topsellers():
    """Manuell trigger via HTTP. Kjører ett kall og returnerer resultatet (trimmet)."""
    try:
        items = await get_top_sellers(limit=10)
        # send også en kort Discord-melding
        titles = [str(i.get("title", ""))[:70] for i in items[:5]]
        await post_discord(
            "🛎️ **Manual Top Sellers Trigger**\n" + "\n".join(f"- {t}" for t in titles)
        )
        return JSONResponse({"ok": True, "count": len(items), "sample": titles})
    except Exception as e:
        await post_discord(f"⚠️ Manual trigger error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# Root kan fortsatt leveres av site_routes (f.eks. /)
# Uvicorn entrypoint: `uvicorn main:app --host 0.0.0.0 --port $PORT`