# site_routes.py
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Dict

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

# Hent Discord-webhook fra env (samme som heartbeat)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()
SERVICE_NAME = os.getenv("SERVICE_NAME", "purebloomworld-agent")

# ===== Dummy produkter (byttes senere av Top Sellers Engine) =====
# url = ekstern affiliate-URL (placeholder nå)
PRODUCTS: List[Dict] = [
    {
        "id": "p1",
        "name": "Magnesium Glycinate (Sleep Stack)",
        "price": "€19.90",
        "img": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?q=80&w=1200&auto=format&fit=crop",
        "url": "https://www.amazon.com/",
        "tags": ["health", "supplements"],
    },
    {
        "id": "p2",
        "name": "Vitamin D3 + K2 Winter Kit",
        "price": "€24.00",
        "img": "https://images.unsplash.com/photo-1623065429920-9b0c4c1a8bf0?q=80&w=1200&auto=format&fit=crop",
        "url": "https://www.amazon.com/",
        "tags": ["health"],
    },
    {
        "id": "p3",
        "name": "USB‑C GaN Travel Charger (65W)",
        "price": "€34.90",
        "img": "https://images.unsplash.com/photo-1586717799252-bd134ad00e26?q=80&w=1200&auto=format&fit=crop",
        "url": "https://www.amazon.com/",
        "tags": ["tech", "gadget"],
    },
    {
        "id": "p4",
        "name": "Bone‑Conduction Workout Headphones",
        "price": "€49.00",
        "img": "https://images.unsplash.com/photo-1545127398-14699f92334b?q=80&w=1200&auto=format&fit=crop",
        "url": "https://www.amazon.com/",
        "tags": ["tech", "fitness"],
    },
    {
        "id": "p5",
        "name": "Refillable Cleaning Concentrate Kit",
        "price": "€17.50",
        "img": "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?q=80&w=1200&auto=format&fit=crop",
        "url": "https://www.amazon.com/",
        "tags": ["eco", "home"],
    },
    {
        "id": "p6",
        "name": "Compostable Kitchen Bags (Leak‑Proof)",
        "price": "€8.90",
        "img": "https://images.unsplash.com/photo-1591994843342-eab662c57c7d?q=80&w=1200&auto=format&fit=crop",
        "url": "https://www.amazon.com/",
        "tags": ["eco"],
    },
]


# ===== Utilities =====
async def post_discord(message: str, username: str = "PBW Clicks") -> bool:
    """Send a small log message to Discord; safe‑fail if no webhook."""
    if not DISCORD_WEBHOOK:
        return False
    payload = {"content": message, "username": username}
    timeout = httpx.Timeout(8.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.post(DISCORD_WEBHOOK, json=payload)
            return r.status_code < 300
        except Exception:
            return False


def page_shell(inner_html: str, title="PureBloomWorld") -> str:
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<meta name="description" content="Curated products & ideas in Health, Lifestyle, Tech and Eco — powered by AI."/>
<style>
:root{{--bg:#0f172a;--panel:#0b1227;--border:#1f2937;--muted:#94a3b8;--text:#e5e7eb;--brand:#22c55e;--brand2:#10b981;--accent:#38bdf8}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial;background:linear-gradient(180deg,var(--bg),#0b1023 60%, #0a0f1f);color:var(--text)}}
.wrap{{max-width:1100px;margin:0 auto;padding:22px}}
header{{display:flex;align-items:center;justify-content:space-between;gap:10px}}
.logo{{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.2px}}
.leaf{{width:28px;height:28px;border-radius:8px;background:radial-gradient(circle at 30% 30%, var(--brand), var(--brand2));display:grid;place-items:center;color:#052e16;font-weight:900}}
nav a{{color:var(--muted);text-decoration:none;margin-left:14px;font-weight:600}}
nav a:hover{{color:var(--text)}}
.panel{{border:1px solid var(--border);background:linear-gradient(180deg,var(--panel),#0a1324);border-radius:18px}}
.hero{{margin:40px 0;padding:26px}}
.hero h1{{margin:0 0 8px;font-size:clamp(28px,4.2vw,44px);line-height:1.1}}
.hero p{{margin:0;color:var(--muted);font-size:clamp(14px,2.3vw,18px)}}
.grid{{display:grid;grid-template-columns:1fr;gap:14px;margin:24px 0}}
@media(min-width:720px){{.grid{{grid-template-columns:repeat(3,1fr)}}}}
.card{{background:#0b1021;border:1px solid var(--border);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}}
.card img{{width:100%;height:170px;object-fit:cover}}
.card .body{{padding:14px;display:flex;flex-direction:column;gap:6px}}
.price{{font-weight:800}}
.btn{{background:linear-gradient(90deg,var(--brand),var(--brand2));color:#052e16;border:none;border-radius:10px;padding:10px 12px;font-weight:800;text-decoration:none;display:inline-block;text-align:center}}
.btn:active{{transform:translateY(1px)}}
footer{{margin:34px 0 10px;color:var(--muted);font-size:13px;text-align:center}}
.muted{{color:var(--muted)}}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo"><div class="leaf">🌱</div><div>PureBloomWorld</div></div>
      <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
      </nav>
    </header>
    {inner_html}
    <footer>© <span id="y"></span> PureBloomWorld — Built with ❤️ + AI · <span class="muted">v1</span></footer>
  </div>
  <script>document.getElementById('y').textContent=new Date().getFullYear()</script>
</body></html>"""


# ===== Pages =====
@router.get("/", response_class=HTMLResponse)
def homepage():
    cards = []
    for p in PRODUCTS:
        # lenke går via /out/{id} og åpner i ny fane hos bruker
        cards.append(f"""
          <div class="card">
            <img src="{p['img']}" alt="{p['name']}"/>
            <div class="body">
              <div style="font-weight:700">{p['name']}</div>
              <div class="price">{p['price']}</div>
              <a class="btn" href="/out/{p['id']}" target="_blank" rel="noopener">Se produkt →</a>
              <div class="muted">#{' #'.join(p['tags'])}</div>
            </div>
          </div>
        """)
    inner = f"""
    <section class="hero panel">
      <h1>Curated products & ideas, powered by AI.</h1>
      <p>We rotate 20–50 top sellers so you always see what the market already loves.</p>
    </section>
    <section class="grid">
      {''.join(cards)}
    </section>
    """
    return HTMLResponse(page_shell(inner, "PureBloomWorld"))


@router.get("/about", response_class=HTMLResponse)
def about():
    inner = """
    <section class="hero panel">
      <h1>About PureBloomWorld</h1>
      <p>We curate Health, Lifestyle, Tech and Eco bestsellers. Market‑driven, no fluff.</p>
    </section>
    """
    return HTMLResponse(page_shell(inner, "About — PureBloomWorld"))


@router.get("/contact", response_class=HTMLResponse)
def contact():
    inner = """
    <section class="hero panel">
      <h1>Contact</h1>
      <p class="muted">Partnerships or product suggestions?</p>
      <p>Email: <a href="mailto:oletom@dinboliggc.com">oletom@dinboliggc.com</a></p>
    </section>
    """
    return HTMLResponse(page_shell(inner, "Contact — PureBloomWorld"))


# ===== Click‑through with Discord logging =====
def _find_product(pid: str) -> Dict:
    for p in PRODUCTS:
        if p["id"] == pid:
            return p
    raise KeyError(pid)


@router.get("/out/{pid}")
async def out_redirect(pid: str):
    """Redirects to external URL in a new tab; logs click to Discord."""
    try:
        p = _find_product(pid)
    except KeyError:
        raise HTTPException(status_code=404, detail="Product not found")

    # Discord‑logg (fire‑and‑forget)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    msg = f"🔗 Click → **{p['name']}** ({pid})  •  {ts}  •  via `{SERVICE_NAME}`"
    asyncio.create_task(post_discord(msg))

    # 307 temporary redirect (bevarer metode)
    return RedirectResponse(url=p["url"], status_code=307)


# ===== Simple JSON feed (kan brukes av agent senere) =====
@router.get("/api/products")
def api_products():
    return JSONResponse({"products": PRODUCTS})