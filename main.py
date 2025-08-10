# main.py — PureBloomWorld Agent (stabil startup)

"""
Hva den gjør:
- Sender startup-ping til Discord
- Heartbeat hver N min (ENV: HEARTBEAT_MINUTES)
- /healthz-endpoint
- Serverer forsiden via site_routes.py
- (valgfritt) Topp­selger-loop i egen background task
ENV:
- DISCORD_WEBHOOK (obligatorisk)
- SERVICE_NAME (default: purebloomworld-agent)
- ENV (default: prod)
- HEARTBEAT_MINUTES (default: 60)
- TOPSELLER_ENABLE (default: false)
- TOPSELLER_INTERVAL_MIN (default: 60)
- GH_TOKEN, GH_OWNER, GH_REPO, GH_BRANCH (valgfritt for commits)
"""

import os, asyncio, time, json
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# --- interne moduler (eksisterer fra før) ---
from site_routes import router as site_router
from gh_push import commit_file, timestamp  # brukes av toppselger-jobb
from products import get_top_sellers        # mock/real, avhengig av din fil

# ---------- Config ----------
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")
ENV = os.getenv("ENV", "prod")
HEARTBEAT_MINUTES = int(os.getenv("HEARTBEAT_MINUTES", "60"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

TOPSELLER_ENABLE = os.getenv("TOPSELLER_ENABLE", "false").lower() in ("1","true","yes")
TOPSELLER_INTERVAL = int(os.getenv("TOPSELLER_INTERVAL_MIN", "60"))

GH_TOKEN  = os.getenv("GH_TOKEN", "").strip()
GH_OWNER  = os.getenv("GH_OWNER", "").strip()
GH_REPO   = os.getenv("GH_REPO", "").strip()
GH_BRANCH = os.getenv("GH_BRANCH", "main").strip()

# ---------- App ----------
app = FastAPI(title="PureBloomWorld Agent", version="1.0.0")
app.include_router(site_router)

STARTED_AT = datetime.now(timezone.utc)
_shutdown = asyncio.Event()


# ---------- Utils ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def post_discord(text: str):
    if not DISCORD_WEBHOOK:
        # Ikke crash – bare logg til stdout
        print(f"[WARN] DISCORD_WEBHOOK mangler, melding ikke sendt: {text[:120]}")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(DISCORD_WEBHOOK, json={"content": text})
            if r.status_code >= 300:
                print(f"[ERR] Discord POST {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[ERR] Discord POST exception: {e}")

async def heartbeat_loop():
    # liten delay for ikke å kollidere med oppstartslogg
    await asyncio.sleep(1.0)
    n = max(1, HEARTBEAT_MINUTES)
    while not _shutdown.is_set():
        try:
            msg = (
                f"💗 Heartbeat {SERVICE_NAME} ({ENV})\n"
                f"• time: {now_iso()}\n"
                f"• heartbeat: every {n} min"
            )
            await post_discord(msg)
        except Exception as e:
            print(f"[ERR] heartbeat_loop: {e}")
        await asyncio.wait_for(_shutdown.wait(), timeout=n * 60)

async def topseller_loop():
    # kjør kun hvis aktivert – og ALDRI blokker oppstart
    if not TOPSELLER_ENABLE:
        print("[INFO] Top-seller loop deaktivert")
        return
    print("[INFO] Top-seller loop startet")
    # liten initial delay
    await asyncio.sleep(2.0)
    interval = max(5, TOPSELLER_INTERVAL)  # minimum 5 min for sikkerhets skyld
    while not _shutdown.is_set():
        try:
            items = get_top_sellers()  # kommer fra products.py (mock/real)
            top5 = ", ".join(i.title for i in items[:5])
            await post_discord(
                f"🛒 Top sellers (mock) — topp 5:\n1. {top5}\n(full liste commits til GitHub)"
            )
            # prøv commit – men ikke crash hvis GH-token mangler
            if GH_TOKEN and GH_OWNER and GH_REPO:
                content = json.dumps([i.__dict__ for i in items], ensure_ascii=False, indent=2)
                path = f"data/topsellers/{timestamp()}.json"
                await commit_file(
                    owner=GH_OWNER,
                    repo=GH_REPO,
                    branch=GH_BRANCH,
                    path=path,
                    content=content,
                    token=GH_TOKEN,
                    commit_message=f"Top sellers {timestamp()} ({SERVICE_NAME})",
                )
            else:
                print("[INFO] Hopper over GitHub commit (mangler GH_* env)")
        except Exception as e:
            # aldri la unntak her stoppe heartbeats eller pings
            print(f"[ERR] topseller_loop: {e}")
        # vent til neste runde
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=interval * 60)
        except asyncio.TimeoutError:
            pass


# ---------- Startup / Shutdown ----------
@app.on_event("startup")
async def on_startup():
    print(f"[START] {SERVICE_NAME} ({ENV}) at {now_iso()}")
    # send oppstarts-ping FØR andre jobber
    await post_discord(
        f"✅ Startup {SERVICE_NAME} ({ENV})\n"
        f"• time: {now_iso()}\n"
        f"• heartbeat: every {HEARTBEAT_MINUTES} min"
    )
    # start background tasks
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(topseller_loop())

@app.on_event("shutdown")
async def on_shutdown():
    print(f"[STOP] {SERVICE_NAME} ({ENV}) at {now_iso()}")
    _shutdown.set()
    await post_discord(f"❗ Shutdown {SERVICE_NAME}\n• time: {now_iso()}")


# ---------- Health & test ----------
@app.get("/healthz")
async def healthz():
    return JSONResponse({"ok": True, "service": SERVICE_NAME, "env": ENV, "time": now_iso()})


# enkel manuell test av Discord uten å redeploye
@app.get("/test/discord")
async def test_discord():
    await post_discord(f"🔧 Test fra {SERVICE_NAME} {now_iso()}")
    return {"sent": True}