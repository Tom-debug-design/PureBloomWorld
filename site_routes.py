# site_routes.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse

router = APIRouter()

@router.get("/healthz")
def healthz():
    return JSONResponse({"ok": True})

@router.get("/status")
def status():
    html = """<!doctype html><meta charset="utf-8">
    <title>PureBloomWorld Status</title>
    <style>body{font-family:system-ui;margin:2rem;}</style>
    <h1>PureBloomWorld – Status</h1>
    <ul>
      <li>Backend: OK</li>
      <li>Heartbeat: aktiv</li>
      <li>GitHub auto-push: aktiv (hvis GH_TOKEN/OWNER/REPO er satt)</li>
      <li>Topseller-loop: styres av TOPSELLER_ENABLE/TOPSELLER_INTERVAL_MIN</li>
    </ul>"""
    return HTMLResponse(html)