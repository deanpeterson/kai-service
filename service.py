# service.py  – API + mini UI that shows *latest* result
# ──────────────────────────────────────────────────────────────────────
import json, os, shutil, subprocess, uuid, difflib                     # <<< added json
from pathlib import Path
from typing import Any                                                  # <<< added

from fastapi import FastAPI, HTTPException, Request, Form              # <<< changed
from fastapi.responses import HTMLResponse, JSONResponse               # <<< added
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="Kai Analysis Service")

# ── paths ────────────────────────────────────────────────────────────
INIT_FILE   = Path("/opt/kai/example/initialize.toml")
TMP_ROOT    = Path("/tmp")
REPO_PREFIX = "repo-"
TEMPLATES   = Jinja2Templates(directory="/opt/templates")

# ── in‑process cache of last run ─────────────────────────────────────
LAST_RESULT: dict[str, Any] | None = None                              # <<< added


class AnalyzeBody(BaseModel):                                          # <<< renamed
    git_url: str


# ── helpers ──────────────────────────────────────────────────────────
def purge_old_repos() -> None:
    for p in TMP_ROOT.glob(f"{REPO_PREFIX}*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def rewrite_initialize_toml(workdir: Path) -> None:
    txt = INIT_FILE.read_text().splitlines(keepends=True)
    out, done = [], False
    for line in txt:
        if line.strip().startswith("root_path"):
            out.append(f'root_path = "{workdir}"\n')
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f'root_path = "{workdir}"\n')
    INIT_FILE.write_text("".join(out))


def init_git_repo(workdir: Path) -> None:
    subprocess.run(["git", "-C", workdir, "init"], check=True)
    subprocess.run(["git", "-C", workdir, "config",
                    "user.email", "kai@localhost"], check=True)
    subprocess.run(["git", "-C", workdir, "config",
                    "user.name",  "Kai Bot"], check=True)
    subprocess.run(["git", "-C", workdir, "add", "."], check=True)
    subprocess.run(["git", "-C", workdir, "commit",
                    "--allow-empty", "-m", "baseline"], check=True)


def make_html_diff(repo: Path) -> str:
    diff_txt = subprocess.check_output(
        ["git", "-C", repo, "diff", "--unified=2", "--no-color"]
    ).decode("utf-8", errors="replace")

    if not diff_txt.strip():
        return "<p><em>No changes produced.</em></p>"

    hd = difflib.HtmlDiff(tabsize=4, wrapcolumn=120)
    # Very small heuristic to build one big table
    left, right = [], []
    for ln in diff_txt.splitlines()[4:]:
        if ln.startswith('-'):
            left.append(ln[1:]); right.append('')
        elif ln.startswith('+'):
            left.append('');     right.append(ln[1:])
        else:
            left.append(ln);     right.append(ln)
    return hd.make_table(left, right,
                         fromdesc="baseline", todesc="patched",
                         context=True, numlines=2)


# ── REST API endpoints ───────────────────────────────────────────────
@app.post("/analyze", response_class=JSONResponse)
def analyze(body: AnalyzeBody):
    global LAST_RESULT                                                 # <<< added
    purge_old_repos()

    workdir = TMP_ROOT / f"{REPO_PREFIX}{uuid.uuid4().hex}"
    subprocess.run(["git", "clone", body.git_url, workdir], check=True)
    init_git_repo(workdir)

    rewrite_initialize_toml(workdir)
    os.chdir("/opt/kai/example")

    proc = subprocess.run(
        ["python3.12", "run_demo.py"],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        raise HTTPException(
            500,
            f"run_demo exit‑code {proc.returncode}\n\n"
            f"{proc.stderr[-4000:]}"
        )

    result = {
        "status":   "ok",
        "repo_path": str(workdir),
        "stdout":   proc.stdout[-4000:],
        "stderr":   proc.stderr[-4000:],
        "html":     make_html_diff(workdir),
    }
    LAST_RESULT = result                                               # <<< added
    return result


@app.get("/latest", response_class=JSONResponse)                       # <<< new
def latest():
    if LAST_RESULT is None:
        return JSONResponse({"detail": "No analysis run yet"}, status_code=404)
    return LAST_RESULT


# ── tiny UI at “/” ───────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "diff_html": (LAST_RESULT or {}).get("html", ""),
        },
    )


# optional: allow simple *form* submission from the page -------------
@app.post("/analyze-form", response_class=HTMLResponse)                # <<< new
def analyze_form(request: Request, git_url: str = Form(...)):
    analyze(AnalyzeBody(git_url=git_url))                              # reuse logic
    return index(request)
