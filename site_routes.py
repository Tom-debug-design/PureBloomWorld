# site_routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from products import get_top_sellers, get_product

router = APIRouter()

@router.get("/healthz")
def healthz():
    return JSONResponse({"ok": True})

@router.get("/topsellers.json")
def topsellers_json():
    return JSONResponse({"items": get_top_sellers(10)})

@router.get("/r/{pid}")
def redirect_aff(pid: str):
    p = get_product(pid)
    if not p or not p.url:
        raise HTTPException(status_code=404, detail="Unknown product")
    # TODO: legg på dine affiliate-parametre/UTM her når du har IDs
    target = p.url  # + "?tag=DIN_AMAZON_TAG" osv.
    return RedirectResponse(url=target, status_code=302)

@router.get("/")
def home():
    items = get_top_sellers(5)
    li = "".join([
        f'''<li style="margin:1rem 0;display:flex;gap:1rem;align-items:center">
            <img src="{x.get("image")}" alt="" width="64" height="64" loading="lazy"/>
            <div style="flex:1">
              <div style="font-weight:600">{x.get("title")}</div>
              <div style="opacity:.7">Score: {x.get("score")}{(" · $" + str(x.get("price"))) if x.get("price") else ""}</div>
            </div>
            <a href="/r/{x.get("id")}" style="padding:.5rem 1rem;border:1px solid #ddd;border-radius:.5rem;text-decoration:none">Se tilbud</a>
        </li>'''
        for x in items
    ])
    html = f"""<!doctype html><meta charset="utf-8">
    <title>PureBloomWorld – Toppselgere</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <style>body{{font-family:system-ui;margin:2rem;max-width:800px}} h1{{margin:0 0 1rem}}</style>
    <h1>Dagens toppselgere</h1>
    <ul style="list-style:none;padding:0;margin:0">{li}</ul>
    """
    return HTMLResponse(html)