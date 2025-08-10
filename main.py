# main.py — diagnostics v3

import os, asyncio, json, hashlib
from datetime import datetime, timezone

print("=== LOADED main.py v3 ===")  # <- vises ved import

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from site_routes import router as site_router
from products import get_top_sellers
from gh_push import commit_file, timestamp

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")
ENV = os.getenv("ENV", "prod")
HEARTBEAT_MINUTES = int(os.getenv("HEARTBEAT_MINUTES", "60"))
DISCORD_WEBHOOK = (os.getenv("DISCORD_WEBHOOK") or "").strip()
TOPSELLER_ENABLE = (os.getenv("TOPSELLER_ENABLE", "false").lower() in ("1","true","yes"))
TOPSELLER_INTERVAL = int(os.getenv("TOPSELLER_INTERVAL_MIN", "60"))
GH_TOKEN  = (os.getenv("GH_TOKEN")  or "").strip()
GH_OWNER  = (os.getenv("GH_OWNER")  or "").strip()
GH_REPO   = (os.getenv("GH_REPO")   or "").strip()
GH_BRANCH = (os.getenv("GH_BRANCH") or "main").strip()

wh_hash = hashlib.sha1(DISCORD_WEBHOOK.encode()).hexdigest()[:8] if DISCORD_WEBHOOK else "MISSING"
print(f"[CFG] SERVICE_NAME={SERVICE_NAME} ENV={ENV} HB={HEARTBEAT_MINUTES}m "
      f"TOPSELLER={TOPSELLER_ENABLE}/{TOPSELLER_INTERVAL}m WH={wh_hash} "
      f"GH={'OK' if GH_TOKEN and GH_OWNER and GH_REPO else 'MISSING'}")

app = FastAPI(title="PureBloomWorld Agent", version="diag-3")
app.include_router(site_router)

_shutdown = asyncio.Event()

async def post_discord(text: str):
    if not DISCORD_WEBHOOK:
        print(f"[DISCORD] webhook missing, skip: {text[:80]}...")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(DISCORD_WEBHOOK, json={"content": text})
            ok = 200 <= r.status_code < 300
            print(f"[DISCORD] POST status={r.status_code} ok={ok} len={len(r.text)}")
            if not ok:
                print(f"[DISCORD] body: {r.text[:300]}")
            return ok
    except Exception as e:
        print(f"[DISCORD] exception: {e}")
        return False

async def heartbeat_loop():
    await asyncio.sleep(1.0)
    while not _shutdown.is_set():
        await post_discord(f"💗 Heartbeat {SERVICE_NAME} ({ENV}) • {now_iso()} • every {HEARTBEAT_MINUTES} min")
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=max(1, HEARTBEAT_MINUTES)*60)
        except asyncio.TimeoutError:
            pass

async def topseller_loop():
    if not TOPSELLER_ENABLE:
        print("[TOPSELLER] disabled")
        return
    print("[TOPSELLER] started")
    await asyncio.sleep(2.0)
    while not _shutdown.is_set():
        try:
            items = get_top_sellers()
            top5 = ", ".join(i.title for i in items[:5])
            await post_discord(f"🛒 Top sellers — 1. {top5}")
            if GH_TOKEN and GH_OWNER and GH_REPO:
                content = json.dumps([i.__dict__ for i in items], ensure_ascii=False, indent=2)
                path = f"data/topsellers/{timestamp()}.json"
                await commit_file(GH_OWNER, GH_REPO, GH_BRANCH, path, content, GH_TOKEN,
                                  f"Top sellers {timestamp()} ({SERVICE_NAME})")
                print("[TOPSELLER] committed to GitHub")
            else:
                print("[TOPSELLER] skip commit (missing GH env)")
        except Exception as e:
            print(f"[TOPSELLER] error: {e}")
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=max(5, TOPSELLER_INTERVAL)*60)
        except asyncio.TimeoutError:
            pass

@app.on_event("startup")
async def on_startup():
    print(f"[STARTUP] firing at {now_iso()} (WH={wh_hash})")
    await post_discord(f"✅ Startup {SERVICE_NAME} ({ENV}) • {now_iso()} • HB {HEARTBEAT_MINUTES}m")
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(topseller_loop())

@app.on_event("shutdown")
async def on_shutdown():
    print(f"[SHUTDOWN] at {now_iso()}")
    _shutdown.set()
    await post_discord(f"❗ Shutdown {SERVICE_NAME} • {now_iso()}")

@app.get("/healthz")
async def healthz():
    return JSONResponse({"ok": True, "service": SERVICE_NAME, "env": ENV, "time": now_iso()})

@app.get("/test/discord")
async def test_discord():
    ok = await post_discord(f"🔧 Test {SERVICE_NAME} • {now_iso()}")
    return {"sent": ok, "webhook_hash": wh_hash}