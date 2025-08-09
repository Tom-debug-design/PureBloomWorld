# gh_push.py
import os, base64, asyncio
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Response, HTTPException

router = APIRouter()

GH_TOKEN  = os.getenv("GH_TOKEN", "").strip()
GH_OWNER  = os.getenv("GH_OWNER", "").strip()
GH_REPO   = os.getenv("GH_REPO", "").strip()
GH_BRANCH = os.getenv("GH_BRANCH", "main").strip()

API_BASE = "https://api.github.com"

def _headers():
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN missing")
    return {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

async def _get_sha(path: str):
    url = f"{API_BASE}/repos/{GH_OWNER}/{GH_REPO}/contents/{path}?ref={GH_BRANCH}"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, headers=_headers())
        if r.status_code == 200:
            return r.json().get("sha")
        if r.status_code == 404:
            return None
        raise HTTPException(status_code=500, detail=f"GitHub GET failed: {r.text}")

async def put_file(path: str, text: str, message: str):
    sha = await _get_sha(path)
    payload = {
        "message": message,
        "content": base64.b64encode(text.encode()).decode(),
        "branch": GH_BRANCH,
        **({"sha": sha} if sha else {}),
    }
    url = f"{API_BASE}/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.put(url, headers=_headers(), json=payload)
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"GitHub PUT failed: {r.text}")
        return r.json()

@router.get("/ops/push-test")
async def push_test():
    """Oppretter pbw_logs/ping-YYYYmmdd-HHMMSS.txt i repoet."""
    if not (GH_TOKEN and GH_OWNER and GH_REPO):
        raise HTTPException(status_code=400, detail="Missing GH_* env vars")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = f"pbw_logs/ping-{ts}.txt"
    text = f"PBW agent ping at {ts}Z\n"
    await put_file(path, text, f"PBW: ping {ts}")
    return Response(content=f"Committed {path}\n", media_type="text/plain")