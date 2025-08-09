# site_routes.py
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

BASE_CSS = """
:root{
  --bg:#0f172a; --panel:#0b1227; --border:#1f2937;
  --muted:#94a3b8; --text:#e5e7eb;
  --brand:#22c55e; --brand2:#10b981; --accent:#38bdf8;
}
*{box-sizing:border-box}
body{
  margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial;
  background:linear-gradient(180deg,var(--bg),#0b1023 60%, #0a0f1f);
  color:var(--text);
}
a{color:inherit}
.wrap{max-width:1100px;margin:0 auto;padding:22px}
header{display:flex;align-items:center;justify-content:space-between;gap:10px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.2px}
.leaf{width:28px;height:28px;border-radius:8px;background:radial-gradient(circle at 30% 30%, var(--brand), var(--brand2));display:grid;place-items:center;color:#052e16;font-weight:900}
nav a{color:var(--muted);text-decoration:none;margin-left:14px;font-weight:600}
nav a:hover{color:var(--text)}
.panel{border:1px solid var(--border);background:linear-gradient(180deg,var(--panel),#0a1324);border-radius:18px}
.hero{margin:40px 0;padding:26px}
.hero h1{margin:0 0 8px;font-size:clamp(28px,4.2vw,44px);line-height:1.1}
.hero p{margin:0;color:var(--muted);font-size:clamp(14px,2.3vw,18px)}
.cta{margin-top:18px;display:flex;gap:12px;flex-wrap:wrap}
.btn{background:linear-gradient(90deg,var(--brand),var(--brand2));color:#052e16;border:none;border-radius:12px;padding:12px 16px;font-weight:800;text-decoration:none;display:inline-block}
.btn.outline{background:transparent;border:1px solid var(--border);color:var(--text)}
.grid{display:grid;grid-template-columns:1fr;gap:14px;margin:24px 0}
@media(min-width:720px){.grid{grid-template-columns:repeat(4,1fr)}}
.card{background:linear-gradient(180deg,#0a1223,#0a1120);border:1px solid var(--border);border-radius:16px;padding:16px;min-height:130px;display:flex;flex-direction:column;justify-content:space-between;text-decoration:none}
.tag{font-size:12px;color:#0ea5e9;background:#0b1220;border:1px solid var(--border);padding:4px 8px;border-radius:999px;width:max-content}
.title{font-weight:700;margin-top:8px}
.section-title{margin:28px 0 8px;font-weight:800}
.products{display:grid;grid-template-columns:1fr;gap:14px}
@media(min-width:720px){.products{grid-template-columns:repeat(3,1fr)}}
.pcard{background:#0b1021;border:1px solid var(--border);border-radius:14px;padding:14px;text-align:left}
.pname{font-weight:700}
.muted{color:var(--muted)}
footer{margin:34px 0 10px;color:var(--muted);font-size:13px;text-align:center}
"""

def page_shell(inner_html: str, title="PureBloomWorld") -> str:
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<meta name="description" content="Curated products & ideas in Health, Lifestyle, Tech and Eco — powered by AI."/>
<style>{BASE_CSS}</style>
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

@router.get("/", response_class=HTMLResponse)
def homepage():
    inner = """
    <section class="hero panel">
      <h1>Curated products & ideas, powered by AI.</h1>
      <p>We research health, lifestyle, tech and eco products — then publish the best picks with honest summaries.</p>
      <div class="cta">
        <a class="btn" href="#categories">Explore categories</a>
        <a class="btn outline" href="/contact">Contact</a>
      </div>
    </section>

    <section id="categories" class="grid">
      <a class="card" href="#" title="Coming soon">
        <span class="tag">Health</span>
        <div><div class="title">Skincare & Supplements</div><div class="muted">Science‑backed picks. No fluff.</div></div>
      </a>
      <a class="card" href="#" title="Coming soon">
        <span class="tag">Lifestyle</span>
        <div><div class="title">Daily Upgrades</div><div class="muted">Sleep, focus, recovery.</div></div>
      </a>
      <a class="card" href="#" title="Coming soon">
        <span class="tag">Tech</span>
        <div><div class="title">Gadgets that matter</div><div class="muted">Tools, not toys.</div></div>
      </a>
      <a class="card" href="#" title="Coming soon">
        <span class="tag">Eco</span>
        <div><div class="title">Sustainable Choices</div><div class="muted">Lower footprint, higher quality.</div></div>
      </a>
    </section>

    <h3 class="section-title">Featured (placeholders)</h3>
    <section class="products">
      <div class="pcard"><div class="pname">Example Product A</div><div class="muted">Short, honest summary about why it’s good.</div><div class="muted">#health #skincare</div></div>
      <div class="pcard"><div class="pname">Example Product B</div><div class="muted">One-liner value prop to test layout.</div><div class="muted">#tech #gadget</div></div>
      <div class="pcard"><div class="pname">Example Product C</div><div class="muted">Sustainable pick placeholder for launch.</div><div class="muted">#eco</div></div>
    </section>
    """
    return HTMLResponse(page_shell(inner, "PureBloomWorld"))

@router.get("/about", response_class=HTMLResponse)
def about():
    inner = """
    <section class="hero panel">
      <h1>About PureBloomWorld</h1>
      <p>We’re building a long‑lived hub that curates products and ideas in Health, Lifestyle, Tech and Eco. Quality first, hype never.</p>
    </section>
    """
    return HTMLResponse(page_shell(inner, "About — PureBloomWorld"))

@router.get("/contact", response_class=HTMLResponse)
def contact():
    inner = """
    <section class="hero panel">
      <h1>Contact</h1>
      <p class="muted">Questions, partnerships, or product suggestions?</p>
      <p>Email: <a href="mailto:oletom@dinboliggc.com">oletom@dinboliggc.com</a></p>
    </section>
    """
    return HTMLResponse(page_shell(inner, "Contact — PureBloomWorld"))