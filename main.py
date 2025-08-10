"""
PureBloomWorld Agent – main.py (single-file)

Hva den gjør:
- Startup-ping til Discord
- Heartbeat hver N minutter (ENV: HEARTBEAT_MINUTES)
- /healthz-endpoint
- Top-seller loop som kjører periodisk (ENV: TOPSELLER_ENABLE, TOPSELLER_INTERVAL_MIN)
- Manuell trigger: GET /trigger/topsellers
- Committer full top-seller-liste til GitHub hvis GH-variabler finnes

ENV-variabler:
- DISCORD_WEBHOOK            (obligatorisk for meldinger)
- SERVICE_NAME               (default: purebloomworld-agent)
- ENV                        (default: prod)
- HEARTBEAT_MINUTES          (default: 60)
- TOPSELLER_ENABLE           (default: false)
- TOPSELLER_INTERVAL_MIN     (default: 60)
- GH_TOKEN / PureBloomWorld / GITHUB_TOKEN (ett av disse må finnes for GitHub-push)
- GH_OWNER                   (GitHub owner/org)
- GH_REPO                    (Repository navn)
- GH_BRANCH                  (default: main)
"""

import os, asyncio, time, json, base64
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

# ---------------- Env helpers ----------------

def getenv_any(*keys: str, default: str = "") -> str:
    for k in keys:
        v = os.getenv(k)
        if v and v.strip():
            return v.strip()
    return default

def getenv_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except Exception:
        return default

def getenv_bool(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    v = v.strip().lower()
    return v in ("1", "true", "yes", "on")

# ---------------- Config ----------------

SERVICE_NAME        = os.getenv("SERVICE_NAME", "purebloomworld-agent").strip()
ENV                 = os.getenv("ENV", "prod").strip()
DISCORD_WEBHOOK     = os.getenv("DISCORD_WEBHOOK", "").strip()

HEARTBEAT_MINUTES   = getenv_int("HEARTBEAT_MINUTES", 60)

TOPSELLER_ENABLE    = getenv_bool("TOPSELLER_ENABLE", False)
TOPSELLER_INTERVAL  = getenv_int("TOPSELLER_INTERVAL_MIN", 60)

# Token-compat: støtter både nytt og gammelt navn
GH_TOKEN            = getenv_any("GH_TOKEN", "PureBloomWorld", "GITHUB_TOKEN", default="")
GH_OWNER            = os.getenv("GH_OWNER", "").strip()
GH_REPO             = os.getenv("GH_REPO", "").strip()
GH_BRANCH           = os.getenv("GH_BRANCH", "main").strip()

# ---------------- App & state ----------------

app = FastAPI(title="PureBloomWorld Agent", version="1.0.0")
_started_at = datetime.now(timezone.utc)
_shutdown = asyncio.Event()

# Bakgrunnsoppgaver
_bg_tasks: list[asyncio.Task] = []

# ---------------- Utils ----------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def discord(msg: str) -> None:
    if not DISCORD_WEBHOOK:
        return
    payload = {"content": msg}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(DISCORD_WEBHOOK, json=payload)
    except Exception:
        # Vi lar den bare feile stille – skal ikke krasje agenten
        pass

async def github_commit_text(path: str, content_text: str, message: str) -> tuple[bool, str]:
    """
    Oppdaterer/lagrer fil i GH_REPO. Returnerer (ok, info).
    Krever: GH_TOKEN, GH_OWNER, GH_REPO
    """
    if not (GH_TOKEN and GH_OWNER and GH_REPO):
        return False, "GitHub creds mangler"

    api_base = "https://api.github.com"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PureBloomWorld-Agent"
    }

    # Finn eksisterende sha (hvis fila finnes)
    sha = None
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as c:
            r = await c.get(f"{api_base}/repos/{GH_OWNER}/{GH_REPO}/contents/{path}", params={"ref": GH_BRANCH})
            if r.status_code == 200:
                sha = r.json().get("sha")
    except Exception as e:
        return False, f"GH sha-lookup feil: {e}"

    b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    body = {
        "message": message,
        "content": b64,
        "branch": GH_BRANCH
    }
    if sha:
        body["sha"] = sha

    try:
        async with httpx.AsyncClient(timeout=20, headers=headers) as c:
            r = await c.put(f"{api_base}/repos/{GH_OWNER}/{GH_REPO}/contents/{path}", json=body)
            if r.status_code in (200, 201):
                return True, "Commit OK"
            else:
                return False, f"Commit HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"Commit feil: {e}"

# ---------------- Mock top-sellers ----------------

def mock_top_sellers(n: int = 5) -> list[str]:
    return [f"Mock Product #{i}" for i in range(1, n + 1)]

def render_top_sellers_md(items: list[str]) -> str:
    lines = [
        f"# Top Sellers – {now_iso()}",
        "",
        "Topp 20 (mock):",
        ""
    ]
    for i, name in enumerate(items, start=1):
        lines.append(f"{i}. {name}")
    lines.append("")
    return "\n".join(lines)

async def run_top_sellers(push_to_github: bool = True) -> None:
    items = mock_top_sellers(20)
    top5 = ", ".join(items[:5])
    await discord(f"🛒 Top sellers (mock) — topp 5:\n1. {top5}\n(full liste commits til GitHub)")

    if push_to_github:
        md = render_top_sellers_md(items)
        ok, info = await github_commit_text(
            path="data/top_sellers.md",
            content_text=md,
            message=f"Top sellers update {now_iso()}"
        )
        if not ok:
            # Meld fra i Discord slik at feilen er synlig, men ikke crash
            await discord(f"⚠️ GitHub commit feilet: {info}")

# ---------------- Background loops ----------------

async def heartbeat_loop() -> None:
    # første ping ved oppstart
    await discord(f"✅ Startup {SERVICE_NAME} ({ENV})\n• time: {now_iso()}\n• heartbeat: every {HEARTBEAT_MINUTES} min")
    if HEARTBEAT_MINUTES <= 0:
        return
    while not _shutdown.is_set():
        await asyncio.sleep(HEARTBEAT_MINUTES * 60)
        await discord(f"💓 Heartbeat {SERVICE_NAME} ({ENV})\n• time: {now_iso()}")

async def topseller_loop() -> None:
    if not TOPSELLER_ENABLE:
        return
    # kjør en gang ved oppstart
    await run_top_sellers(push_to_github=True)
    # deretter intervall
    interval = max(1, TOPSELLER_INTERVAL) * 60
    while not _shutdown.is_set():
        await asyncio.sleep(interval)
        await run_top_sellers(push_to_github=True)

# ---------------- FastAPI lifecycle ----------------

@app.on_event("startup")
async def on_startup():
    # start loops
    hb = asyncio.create_task(heartbeat_loop())
    _bg_tasks.append(hb)
    ts = asyncio.create_task(topseller_loop())
    _bg_tasks.append(ts)

@app.on_event("shutdown")
async def on_shutdown():
    _shutdown.set()
    for t in _bg_tasks:
        t.cancel()
    await discord(f"❗️Shutdown {SERVICE_NAME}\n• time: {now_iso()}")

# ---------------- Routes ----------------

@app.get("/healthz")
async def healthz():
    return JSONResponse({
        "service": SERVICE_NAME,
        "env": ENV,
        "started_at": _started_at.isoformat(timespec="seconds"),
        "now": now_iso(),
        "heartbeat_minutes": HEARTBEAT_MINUTES,
        "topseller_enable": TOPSELLER_ENABLE,
        "topseller_interval_min": TOPSELLER_INTERVAL,
        "gh_owner": bool(GH_OWNER),
        "gh_repo": bool(GH_REPO),
        "gh_token_present": bool(GH_TOKEN),  # viser ikke verdien
    })

@app.get("/trigger/topsellers")
async def trigger_topsellers():
    # kjør én runde manuelt – nyttig for testing
    await run_top_sellers(push_to_github=True)
    return JSONResponse({"ok": True, "run": "topsellers", "time": now_iso()})

# ---------------- Entry (for uvicorn) ----------------

# Railway kjører `uvicorn main:app` via Procfile, så ingen if __name__ == "__main__" trengs.