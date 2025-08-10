# gh_push.py
import os, base64, httpx, time

GH_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
GH_OWNER = os.getenv("GH_OWNER", "").strip()
GH_REPO  = os.getenv("GH_REPO", "").strip()
GH_BRANCH= os.getenv("GH_BRANCH", "main").strip()

API = "https://api.github.com"

def _gh_headers():
    if not GH_TOKEN:
        raise RuntimeError("Missing GH token (GH_TOKEN/GITHUB_TOKEN/GH_PAT).")
    return {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pbw-agent"
    }

def commit_file(path: str, content: str, message: str):
    """
    Upsert en enkel tekstfil til repoet.
    """
    if not (GH_OWNER and GH_REPO and GH_BRANCH):
        raise RuntimeError("GH_OWNER/GH_REPO/GH_BRANCH must be set.")

    url = f"{API}/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"
    with httpx.Client(timeout=30) as cx:
        # Finn eksisterende sha (om fil finnes)
        r = cx.get(url, params={"ref": GH_BRANCH}, headers=_gh_headers())
        sha = r.json().get("sha") if r.status_code == 200 else None

        data = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": GH_BRANCH
        }
        if sha: data["sha"] = sha

        r2 = cx.put(url, json=data, headers=_gh_headers())
        if r2.status_code not in (200,201):
            raise RuntimeError(f"GitHub push failed: {r2.status_code} {r2.text}")
    return True

def timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())