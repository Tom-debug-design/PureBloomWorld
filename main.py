"""
PureBloomWorld Agent (one-file)

Funksjoner:
- Startup-ping til Discord
- Heartbeat hvert N min (ENV HEARTBEAT_MINUTES; min 1)
- Top-seller loop (mock): Discord + commit JSON til GitHub
- Enkle ops-endpoints

ENV:
- DISCORD_WEBHOOK (valgfri)
- SERVICE_NAME (default: purebloomworld-agent)
- ENV (default: prod)
- HEARTBEAT_MINUTES (default: 60, men aldri < 1)

GitHub (autopush):
- GH_TOKEN (PAT med 'repo')
- GH_OWNER (eks: Tom-debug-design)
- GH_REPO (eks: PureBloomWorld)
- GH_BRANCH (eks: main)

Top-seller:
- TOPSELLER_ENABLED (true/false; default false)
- TOPSELLER_INTERVAL_MIN (default 60, min 15)
"""

import os
import asyncio
import base64
import json
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.responses import JSONResponse, HTMLResponse

# ------------- ENV & konfig -------------
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")
ENV = os.getenv("ENV", "prod")

# Heartbeat med sikker default (aldri 0)
def _int_env(name: str, default: int, min_val: int = None) -> int:
    try:
        v = int(os.getenv(name, str(default)))
    except Exception:
        v = default
    if min_val is not None:
        v = max(min_val, v)
    return v

HEARTBEAT_MINUTES = _int_env("HEARTBEAT_MINUTES", 60, min_val=1)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

# GitHub
GH_TOKEN  = os.getenv("GH_TOKEN", "").strip()
GH_OWNER  = os.getenv("GH_OWNER", "").strip()
GH_REPO   = os.getenv("GH_REPO", "").strip()
GH_BRANCH = os.getenv("GH_BRANCH", "main").strip()

# Top-seller
TOPSELLER_ENABLED = os.getenv("TOPSELLER_ENABLED", "false").lower() in ("1", "true", "yes")
TOPSELLER_INTERVAL_MIN = _int_env("TOPSELLER_INTERVAL_MIN", 60, min_val=15)

# ------------- App -------------
app = FastAPI(title="PureBloomWorld Agent", version="1.2.0")

_started = False  # unngå dobbelt-planlegging ved varme redeploys

# ------------- Discord util -------------
async def send_discord_message(content: str):
    """Sender melding til Discord hvis webhook finnes (stille ved feil)."""
    if not DISCORD_WEBHOOK:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(DISCORD_WEBHOOK, json={"content": content})
    except Exception as e:
        print(f"❌ Discord-feil: {e}")

# ------------- GitHub helpers (Contents API) -------------
def _gh_headers():
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN mangler")
    return {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

async def _gh_get_sha(path: str):
    url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}?ref={GH_BRANCH}"
    async with httpx.AsyncClient(timeout=12) as c:
        r = await c.get(url, headers=_gh_headers())
        if r.status_code == 200:
            return r.json().get("sha")
        if r.status_code == 404:
            return None
        raise HTTPException(status_code=500, detail=f"GitHub GET feilet: {r.text}")

async def gh_put_file(path: str, text: str, message: str):
    sha = await _gh_get_sha(path)
    payload = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": GH_BRANCH,
        **({"sha": sha} if sha else {}),
    }
    url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.put(url, headers=_gh_headers(), json=payload)
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"GitHub PUT feilet: {r.text}")
        return r.json()

# ------------- Heartbeat -------------
async def heartbeat_loop():
    while True:
        await asyncio.sleep(HEARTBEAT_MINUTES * 60)
        await send_discord_message(
            f"🫀 Heartbeat {SERVICE_NAME} ({ENV})\n"
            f"• time: {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
        )

# ------------- Top-seller (mock) -------------
def _mock_fetch_top_sellers(limit: int = 10):
    """Erstattes senere med ekte kilder (Amazon PA-API, CJ, Awin …)."""
    base = "https://example.com/product/"
    out = []
    for i in range(1, limit + 1):
        out.append({
            "rank": i,
            "title": f"Mock Product #{i}",
            "url": f"{base}{i}",
            "price": round(19.99 + i, 2),
            "source": "mock",
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    return out

async def _topseller_run_once():
    items = _mock_fetch_top_sellers(limit=10)

    # kort Discord-sammendrag
    names = ", ".join([f"{x['rank']}. {x['title']}" for x in items[:5]])
    await send_discord_message(
        f"🛒 Top sellers (mock) — topp 5:\n{names}\n"
        f"(full liste commits til GitHub)"
    )

    # commit hele lista
    ts = datetime.now(timezone.utc)
    fname = f"pbw_data/top_sellers-{ts.strftime('%Y%m%d')}.json"
    await gh_put_file(
        fname,
        json.dumps(items, ensure_ascii=False, indent=2),
        f"PBW: top_sellers {ts.isoformat(timespec='seconds')}"
    )

async def topseller_scheduler():
    if not TOPSELLER_ENABLED:
        print("ℹ️ Top-seller loop er av (TOPSELLER_ENABLED=false)")
        return
    # første kjøring kort tid etter oppstart
    await asyncio.sleep(5)
    while True:
        try:
            await _topseller_run_once()
        except Exception as e:
            await send_discord_message(f"⚠️ Top-seller run feilet: {e}")
            print("Top-seller error:", e)
        await asyncio.sleep(TOPSELLER_INTERVAL_MIN * 60)

# ------------- Startup -------------
@app.on_event("startup")
async def startup_event():
    global _started
    if _started:
        return
    _started = True

    await send_discord_message(
        f"✅ Startup {SERVICE_NAME} ({ENV})\n"
        f"• time: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        f"• heartbeat: every {HEARTBEAT_MINUTES} min"
    )

    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(topseller_scheduler())

# ------------- Routes -------------
@app.get("/", response_class=HTMLResponse)
async def root():
    return f"""
    <html><body style="font-family:system-ui;padding:24px">
      <h1>PureBloomWorld Agent</h1>
      <p>Status OK. Se <code>/healthz</code> og <code>/env</code>.</p>
      <ul>
        <li>/ops/ping</li>
        <li>/ops/push-test</li>
        <li>POST /ops/push (JSON: {{ "path": "...", "content": "...", "message": "..." }})</li>
        <li>/ops/top/run</li>
      </ul>
    </body></html>
    """

@app.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "env": ENV,
        "heartbeat_minutes": HEARTBEAT_MINUTES,
        "topseller_enabled": TOPSELLER_ENABLED,
        "topseller_interval_min": TOPSELLER_INTERVAL_MIN,
        "has_discord_webhook": bool(DISCORD_WEBHOOK),
        "has_github": bool(GH_TOKEN and GH_OWNER and GH_REPO),
    }

@app.get("/env")
async def env_view():
    return {
        "SERVICE_NAME": SERVICE_NAME,
        "ENV": ENV,
        "HEARTBEAT_MINUTES": HEARTBEAT_MINUTES,
        "TOPSELLER_ENABLED": TOPSELLER_ENABLED,
        "TOPSELLER_INTERVAL_MIN": TOPSELLER_INTERVAL_MIN,
        "GH_OWNER": GH_OWNER,
        "GH_REPO": GH_REPO,
        "GH_BRANCH": GH_BRANCH,
        "DISCORD_WEBHOOK_set": bool(DISCORD_WEBHOOK),
        "GH_TOKEN_set": bool(GH_TOKEN),
    }

@app.get("/ops/ping")
async def ops_ping():
    return {"pong": True, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}

@app.get("/ops/push-test")
async def push_test():
    if not (GH_TOKEN and GH_OWNER and GH_REPO):
        raise HTTPException(status_code=400, detail="GH_* env mangler")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = f"pbw_logs/ping-{ts}.txt"
    text = f"PBW agent ping at {ts}Z\n"
    await gh_put_file(path, text, f"PBW: ping {ts}")
    await send_discord_message(f"📤 GitHub push OK: `{path}`")
    return Response(content=f"Committed {path}\n", media_type="text/plain")

@app.post("/ops/push")
async def ops_push(
    path: str = Body(..., embed=True),
    content: str = Body(..., embed=True),
    message: str = Body("PBW autopush", embed=True),
):
    if not (GH_TOKEN and GH_OWNER and GH_REPO):
        raise HTTPException(status_code=400, detail="GH_* env mangler")
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="Ugyldig path")
    result = await gh_put_file(path, content, message)
    await send_discord_message(f"📤 GitHub push OK: `{path}`")
    return {"ok": True, "result": result}

@app.get("/ops/top/run")
async def ops_top_run():
    await _topseller_run_once()
    return {"ok": True, "ran": True, "interval_min": TOPSELLER_INTERVAL_MIN}