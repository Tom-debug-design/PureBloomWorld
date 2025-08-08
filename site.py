# site.py
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PBW_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PureBloomWorld</title>
  <style>
    :root{
      --bg:#0f172a; --card:#111827; --muted:#94a3b8; --text:#e5e7eb;
      --brand:#22c55e; --brand-2:#10b981; --accent:#38bdf8;
    }
    *{box-sizing:border-box}
    body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial;
      background:linear-gradient(180deg,var(--bg),#0b1023 60%, #0a0f1f);color:var(--text)}
    .wrap{max-width:1100px;margin:0 auto;padding:24px}
    header{display:flex;align-items:center;justify-content:space-between;gap:12px}
    .logo{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.3px}
    .logo .leaf{width:28px;height:28px;border-radius:8px;background:radial-gradient(circle at 30% 30%, var(--brand), var(--brand-2));display:grid;place-items:center;color:#052e16;font-weight:900}
    nav a{color:var(--muted);text-decoration:none;margin-left:14px;font-weight:600}
    nav a:hover{color:var(--text)}
    .hero{margin:42px 0;padding:28px;border:1px solid #1f2937;background:linear-gradient(180deg,#0b1227,#0a1324);border-radius:18px}
    .hero h1{margin:0 0 10px;font-size:clamp(28px,4.2vw,44px);line-height:1.1}
    .hero p{margin:0;color:var(--muted);font-size:clamp(14px,2.3vw,18px)}
    .cta{margin-top:18px;display:flex;gap:12px;flex-wrap:wrap}
    .btn{background:linear-gradient(90deg,var(--brand),var(--brand-2));color:#052e16;border:none;border-radius:12px;padding:12px 16px;font-weight:800;text-decoration:none;display:inline-block}
    .btn.outline{background:transparent;border:1px solid #1f2937;color:var(--text)}
    .grid{display:grid;grid-template-columns:1fr;gap:14px;margin:24px 0}
    @media(min-width:720px){.grid{grid-template-columns:repeat(4,1fr)}}
    .card{background:linear-gradient(180deg,#0a1223,#0a1120);border:1px solid #1f2937;border-radius:16px;padding:16px;min-height:130px;display:flex;flex-direction:column;justify-content:space-between}
    .tag{font-size:12px;color:#0ea5e9;background:#0b1220;border:1px solid #1f2937;padding:4px 8px;border-radius:999px;width:max-content}
    .title{font-weight:700;margin-top:8px}
    footer{margin:30px 0 10px;color:var(--muted);font-size:13px;text-align:center}
    .muted{color:var(--muted)}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo"><div class="leaf">🌱</div><div>PureBloomWorld</div></div>
      <nav>
        <a href="#health">Health</a>
        <a href="#lifestyle">Lifestyle</a>
        <a href="#tech">Tech</a>
        <a href="#eco">Eco</a>
      </nav>
    </header>

    <section class="hero">
      <h1>Curated products & ideas, powered by AI.</h1>
      <p>We research health, lifestyle, tech and eco products — then publish the best picks with honest, useful summaries.</p>
      <div class="cta">
        <a class="btn" href="#categories">Explore categories</a>
        <a class="btn outline" href="mailto:oletom@dinboliggc.com">Contact</a>
      </div>
    </section>

    <section id="categories" class="grid">
      <a id="health" class="card" href="#" title="Coming soon">
        <span class="tag">Health</span>
        <div>
          <div class="title">Skincare & Supplements</div>
          <div class="muted">Science-backed picks. No fluff.</div>
        </div>
      </a>
      <a id="lifestyle" class="card" href="#" title="Coming soon">
        <span class="tag">Lifestyle</span>
        <div>
          <div class="title">Daily Upgrades</div>
          <div class="muted">Sleep, focus, recovery.</div>
        </div>
      </a>
      <a id="tech" class="card" href="#" title="Coming soon">
        <span class="tag">Tech</span>
        <div>
          <div class="title">Gadgets that matter</div>
          <div class="muted">Tools, not toys.</div>
        </div>
      </a>
      <a id="eco" class="card" href="#" title="Coming soon">
        <span class="tag">Eco</span>
        <div>
          <div class="title">Sustainable Choices</div>
          <div class="muted">Lower footprint, higher quality.</div>
        </div>
      </a>
    </section>

    <footer>
      © <span id="y"></span> PureBloomWorld — Built with ❤️ + AI · <span class="muted">v1</span>
    </footer>
  </div>

  <script>document.getElementById('y').textContent=new Date().getFullYear()</script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
async def homepage():
    return HTMLResponse(content=PBW_HTML, status_code=200)