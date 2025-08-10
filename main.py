"""
PureBloomWorld Agent – Build 1 (autopush + crash warning + health/status)

ENV (må/min):
- DISCORD_WEBHOOK  (må)
- SERVICE_NAME     (default: purebloomworld-agent)
- ENV              (default: prod)
- HEARTBEAT_MINUTES (default: 60)

GitHub (for auto-push):
- GH_TOKEN  (eller GITHUB_TOKEN / GH_PAT)
- GH_OWNER
- GH_REPO
- GH_BRANCH (default: main)

Topseller-loop (placeholder):
- TOPSELLER_ENABLE        (true/false, default: false)
- TOPSELLER_INTERVAL_MIN  (default: 60)
"""
import os, asyncio, time, json
from datetime import datetime, timezone
import httpx

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from site_routes import router as site_router
from gh_push import commit_file, timestamp

# ---------- Config ----------
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")
ENV = os.getenv("ENV", "prod")
HEARTBEAT_MINUTES = int(os.getenv("HEARTBEAT_MINUTES", "60"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

TOPSELLER_ENABLE = os.getenv("TOPSELLER_ENABLE", "false").lower() in ("1","true","yes")
TOPSELLER_INTERVAL_MIN = int(os.getenv("TOPSELLER_INTERVAL_MIN", "60"))

# ---------- Internal state ----------
STARTED_AT = datetime.now(timezone.utc)
_shutdown = asyncio.Event()

app = FastAPI(title="PureBloomWorld Agent", version="1.1.0")
app.include_router(site_router)

# ---------- Utils ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def post_discord(payload: dict):
    if not DISCORD_WEBHOOK: return
    async with httpx.AsyncClient(timeout=20) as cx:
        try:
            await cx.post(DISCORD_WEBHOOK, json=payload)
        except Exception:
            pass

async def discord_ok(title: str, lines: list[str]):
    await post_discord({"content": f"✅ **{title}**\n" + "\n".join(lines)})

async def discord_warn(title: str, lines: list[str]):
    await post_discord({"content": f"❗ **{title}**\n" + "\n".join(lines)})

# ---------- Background tasks ----------
async def heartbeat_loop():
    if HEARTBEAT_MINUTES <= 0:
        return
    while not _shutdown.is_set():
        await asyncio.sleep(HEARTBEAT_MINUTES * 60)
        await discord_ok("Heartbeat " + SERVICE_NAME, [
            f"time: {now_iso()}",
            f"env: {ENV}",
            f"interval_min: {HEARTBEAT_MINUTES}"
        ])
        # push en lettvektslogg til GitHub (hvis satt)
        try:
            log = f"{timestamp()} heartbeat {SERVICE_NAME} env={ENV}\n"
            commit_file("logs/heartbeat.log", log, "chore: heartbeat")
        except Exception:
            pass

async def topseller_loop():
    if not TOPSELLER_ENABLE:
        return
    while not _shutdown.is_set():
        # placeholder: her vil vi senere fylle på med ordentlig toppliste
        stub = {
            "time": now_iso(),
            "note": "topseller stub – erstattes med ekte data i Build 2",
            "items": []
        }
        try:
            commit_file("data/topseller.json", json.dumps(stub, ensure_ascii=False, indent=2),
                        "feat: update topseller stub")
        except Exception:
            pass
        await discord_ok("Topseller stub publisert", [f"time: {now_iso()}", f"items: 0"])
        await asyncio.sleep(max(1, TOPSELLER_INTERVAL_MIN) * 60)

# ---------- FastAPI lifespan ----------
@app.on_event("startup")
async def startup_event():
    await discord_ok("Startup " + SERVICE_NAME + f" ({ENV})", [
        f"time: {now_iso()}",
        f"heartbeat: every {HEARTBEAT_MINUTES} min"
    ])
    # start bakgrunnsjobber
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(topseller_loop())

@app.on_event("shutdown")
async def shutdown_event():
    _shutdown.set()
    await discord_warn("Shutdown " + SERVICE_NAME, [f"time: {now_iso()}"])

# ---------- Minimal API ----------
@app.get("/")
def root():
    return JSONResponse({"ok": True, "service": SERVICE_NAME, "env": ENV})

# Global crash hook
def handle_exception(loop, context):
    msg = context.get("exception") or context.get("message") or "unknown error"
    asyncio.create_task(discord_warn("Crash " + SERVICE_NAME, [str(msg)]))
    # prøv å skrive crashlogg til GitHub
    try:
        entry = f"{timestamp()} CRASH {SERVICE_NAME}: {msg}\n"
        commit_file("logs/crash.log", entry, "fix: crash log")
    except Exception:
        pass

asyncio.get_event_loop().set_exception_handler(handle_exception)