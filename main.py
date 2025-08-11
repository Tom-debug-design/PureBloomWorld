"""
PureBloomWorld Agent — stabil base

Hva den gjør:
- Startup-ping til Discord (+ ENV-dump light)
- Heartbeat hver N minutter (ENV: HEARTBEAT_MINUTES, >0)
- /healthz, /debug/ping
- Manuell trigger: GET /trigger/topsellers (poster topp 5 fra mock-DB)
- (Valgfritt) bakgrunnsloop for top-sellers hvert M min hvis TOPSELLER_ENABLE=true

ENV (Railway):
- DISCORD_WEBHOOK         (påkrevd)
- SERVICE_NAME            (default: purebloomworld-agent)
- HEARTBEAT_MINUTES       (default: 60)  # bruk 1 for rask test, ikke "00"
- TOPSELLER_ENABLE        (default: false)
- TOPSELLER_INTERVAL_MIN  (default: 60)
- GH_TOKEN                (valgfri; kreves for commit)
- GH_OWNER, GH_REPO, GH_BRANCH (kreves bare hvis GH_TOKEN satt)
"""

import os, asyncio, json
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# --- Lokal mock av produkter
from products import get_top_sellers

app = FastAPI()
UTC = timezone.utc

# -------- Config helpers --------
def env_bool(name: str, default: bool=False) -> bool:
    val = os.getenv(name, "").strip().lower()
    if val in ("1","true","yes","y","on"): return True
    if val in ("0","false","no","n","off"): return False
    return default

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except Exception:
        return default

SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent").strip()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()
HEARTBEAT_MINUTES = env_int("HEARTBEAT_MINUTES", 60)

TOPSELLER_ENABLE = env_bool("TOPSELLER_ENABLE", False)
TOPSELLER_INTERVAL_MIN = env_int("TOPSELLER_INTERVAL_MIN", 60)

GH_TOKEN  = os.getenv("GH_TOKEN", "").strip()
GH_OWNER  = os.getenv("GH_OWNER", "").strip()
GH_REPO   = os.getenv("GH_REPO", "").strip()
GH_BRANCH = os.getenv("GH_BRANCH", "main").strip()

# -------- Discord helpers --------
async def discord_send(message: str):
    if not DISCORD_WEBHOOK:
        return
    payload = {"content": message}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(DISCORD_WEBHOOK, json=payload)
        except Exception:
            pass  # aldri crash appen pga Discord

def ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

# -------- GitHub commit (valgfritt) --------
async def commit_list_to_github(filename: str, content: str) -> bool:
    """
    Oppretter/oppdaterer en fil i repo hvis GH_TOKEN/OWNER/REPO er satt.
    Returnerer True ved suksess, ellers False. Ingen exceptions bobler opp.
    """
    if not (GH_TOKEN and GH_OWNER and GH_REPO and GH_BRANCH):
        return False

    api_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "PureBloomWorld-Agent"
    }

    import base64
    b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        # Finn sha hvis fil finnes
        sha = None
        try:
            r_get = await client.get(api_url, params={"ref": GH_BRANCH})
            if r_get.status_code == 200:
                sha = r_get.json().get("sha")
        except Exception:
            pass

        data = {
            "message": f"chore: update {filename} [{ts()}]",
            "content": b64,
            "branch": GH_BRANCH
        }
        if sha: data["sha"] = sha

        try:
            r_put = await client.put(api_url, json=data)
            return r_put.status_code in (200,201)
        except Exception:
            return False

# -------- Schedulers --------
async def heartbeat_loop():
    if HEARTBEAT_MINUTES <= 0:
        return
    while True:
        await discord_send(f"💓 Heartbeat {SERVICE_NAME}\n• time: {ts()}\n• heartbeat: every {HEARTBEAT_MINUTES} min")
        await asyncio.sleep(HEARTBEAT_MINUTES * 60)

async def topseller_loop():
    if not TOPSELLER_ENABLE:
        return
    # første run med en liten delay, deretter fast intervall
    await asyncio.sleep(5)
    while True:
        await run_topsellers(post_to_discord=True, try_commit=True)
        await asyncio.sleep(max(TOPSELLER_INTERVAL_MIN, 1) * 60)

# -------- Core job --------
async def run_topsellers(post_to_discord: bool, try_commit: bool):
    items = get_top_sellers(limit=5)
    line = "🛒 Top sellers (mock) — topp 5:\n" + \
           "".join([f"{i+1}. {p['title']}\n" for i, p in enumerate(items)])
    if post_to_discord:
        await discord_send(line + "(full liste committes til GitHub)")
    if try_commit:
        if GH_TOKEN and GH_OWNER and GH_REPO:
            full_json = json.dumps(items, indent=2, ensure_ascii=False)
            ok = await commit_list_to_github("data/top_sellers.json", full_json)
            if not ok:
                await discord_send("⚠️ Klarte ikke å committe til GitHub (sjekk GH_* vars).")
        else:
            await discord_send("⚠️ Skipper GitHub-commit: GH_TOKEN/OWNER/REPO ikke satt.")

# -------- FastAPI lifecycle & routes --------
@app.on_event("startup")
async def startup_event():
    await discord_send(f"✅ Startup {SERVICE_NAME} (prod)\n• time: {ts()}\n• heartbeat: every {HEARTBEAT_MINUTES} min")
    # start tasks
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(topseller_loop())

@app.get("/healthz")
async def healthz():
    return JSONResponse({"ok": True, "service": SERVICE_NAME, "time": ts()})

@app.get("/debug/ping")
async def debug_ping():
    await discord_send(f"🔧 Debug ping fra {SERVICE_NAME} @ {ts()}")
    return {"sent": True}

@app.get("/trigger/topsellers")
async def trigger_topsellers():
    await run_topsellers(post_to_discord=True, try_commit=True)
    return {"ok": True, "time": ts()}