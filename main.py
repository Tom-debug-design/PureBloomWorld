"""
PureBloomWorld Agent

- Startup-ping til Discord (hvis webhook er satt)
- Heartbeat hver N min (ENV: HEARTBEAT_MINUTES; min 1)
- /healthz og /env
- Forside/produkter via site_routes.py
- Daglig idé-drop kl. 08:00 Europe/Oslo (idea_jobs)  ← post_func=send_discord_message
- Manuell trigger: GET /trigger/ideas
- GitHub autopush:
    • GET /ops/push-test   → pbw_logs/ping-*.txt
    • POST /ops/push       → JSON {path, content, message}

ENV:
- DISCORD_WEBHOOK   (valgfri – uten den hopper vi over Discord-ping)
- SERVICE_NAME      (default: purebloomworld-agent)
- ENV               (default: prod)
- HEARTBEAT_MINUTES (default: 60, men aldri < 1)

GitHub (for autopush):
- GH_TOKEN   (PAT med 'repo')
- GH_OWNER   (eks: Tom-debug-design)
- GH_REPO    (eks: PureBloomWorld)
- GH_BRANCH  (eks: main)
"""

import os
import asyncio
from datetime import datetime, timezone
import base64

import httpx
from fastapi import FastAPI, Response, HTTPException, Body
from fastapi.responses import JSONResponse

from site_routes import router as site_router
from idea_jobs import daily_ideas_scheduler, compose_idea_message

# --------- Config ---------
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")
ENV = os.getenv("ENV", "prod")

# Fallback + min 1 minutt uansett
try:
    _hb_raw = os.getenv("HEARTBEAT_MINUTES", "60")
    HEARTBEAT_MINUTES = max(1, int(_hb_raw))
except Exception:
    HEARTBEAT_MINUTES = 1

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

# GitHub env (autopush)
GH_TOKEN  = os.getenv("GH_TOKEN", "").strip()
GH_OWNER  = os.getenv("GH_OWNER", "").strip()
GH_REPO   = os.getenv("GH_REPO", "").strip()
GH_BRANCH = os.getenv("GH_BRANCH", "main").strip()

# --------- App ---------
app = FastAPI(title="PureBloomWorld Agent", version="1.1.0")
app.include_router(site_router)

# intern vakt for å unngå dobbelt-planlegging
_started = False

# --------- Discord util ---------
async def send_discord_message(content: str):
    """Sender melding til Discord hvis webhook finnes (ikke crash ved feil)."""
    if not DISCORD_WEBHOOK:
        print("⚠️  Ingen DISCORD_WEBHOOK satt – hopper over Discord-ping.")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(DISCORD_WEBHOOK, json={"content": content})
    except Exception as e:
        print(f"❌ Feil ved sending til Discord: {e}")

# --------- Startup/Heartbeat ---------
@app.on_event("startup")
async def startup_event():
    global _started
    if _started:
        # Kan skje ved varme redeploys – ikke planlegg nye tasks
        return
    _started = True

    await send_discord_message(
        f"✅ Startup {SERVICE_NAME} ({ENV})\n"
        f"• time: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        f"• heartbeat: every {HEARTBEAT_MINUTES} min"
    )

    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(daily_ideas_scheduler(post_func=send_discord_message))

async def heartbeat_loop():
    while True:
        await asyncio.sleep(HEARTBEAT_MINUTES * 60)
        await send_discord_message(
            f"🫀 Heartbeat {SERVICE_NAME} ({ENV})\n"
            f"• time: {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
        )

# --------- Health & Env ---------
@app.get("/healthz")
async def health_check():
    return JSONResponse({
        "healthy": True,
        "service": SERVICE_NAME,
        "env": ENV,
        "heartbeat_minutes": HEARTBEAT_MINUTES,
        "has_webhook": bool(DISCORD_WEBHOOK),
        "has_github": bool(GH_TOKEN and GH_OWNER and GH_REPO),
    })

@app.get("/env")
async def env_view():
    # Viser kun ufarlige verdier
    return {
        "SERVICE_NAME": SERVICE_NAME,
        "ENV": ENV,
        "HEARTBEAT_MINUTES": HEARTBEAT_MINUTES,
        "GH_OWNER": GH_OWNER,
        "GH_REPO": GH_REPO,
        "GH_BRANCH": GH_BRANCH,
        "DISCORD_WEBHOOK_set": bool(DISCORD_WEBHOOK),
        "GH_TOKEN_set": bool(GH_TOKEN),
    }

# --------- Manual ideas trigger ---------
@app.get("/trigger/ideas")
async def trigger_ideas():
    msg = compose_idea_message()
    await send_discord_message(msg)
    return {"status": "sent", "message": msg}

# =========================
# GitHub autopush (Contents API)
# =========================

def _gh_headers():
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN missing")
    return {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

async def _gh_get_sha(path: str):
    url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}?ref={GH_BRANCH}"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, headers=_gh_headers())
        if r.status_code == 200:
            return r.json().get("sha")
        if r.status_code == 404:
            return None
        raise HTTPException(status_code=500, detail=f"GitHub GET failed: {r.text}")

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
            raise HTTPException(status_code=500, detail=f"GitHub PUT failed: {r.text}")
        return r.json()

@app.get("/ops/ping")
async def ops_ping():
    return {"pong": True, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}

@app.get("/ops/push-test")
async def push_test():
    """Oppretter pbw_logs/ping-YYYYmmdd-HHMMSS.txt i repoet."""
    if not (GH_TOKEN and GH_OWNER and GH_REPO):
        raise HTTPException(status_code=400, detail="Missing GH_* env vars")
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
    """Generisk push-endpoint. Body:
       { "path": "pbw_logs/custom.txt", "content": "hello", "message": "note" }
    """
    if not (GH_TOKEN and GH_OWNER and GH_REPO):
        raise HTTPException(status_code=400, detail="Missing GH_* env vars")
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")
    result = await gh_put_file(path, content, message)
    await send_discord_message(f"📤 GitHub push OK: `{path}`")
    return {"ok": True, "result": result}