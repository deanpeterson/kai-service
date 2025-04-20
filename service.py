# service.py
import os, shutil, subprocess, tempfile, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Kai Analysis Service")

class Request(BaseModel):
    git_url: str

@app.post("/analyze")
def analyze(req: Request):
    workdir = Path("/tmp") / f"repo-{uuid.uuid4().hex}"
    try:
        # 1) clone dynamically‑provided repo
        subprocess.run(["git", "clone", req.git_url, str(workdir)], check=True)

        # 2) reset ENV so Kai picks the new root
        os.environ["ROOT_PATH"] = str(workdir)           # read by initialize.toml
        os.chdir("/opt/kai/app/example")

        # 3) run demo (stderr merged, capture output)
        proc = subprocess.run(
            ["python", "run_demo.py"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise HTTPException(500, proc.stderr[-4000:])

        return {"status": "ok", "stdout": proc.stdout[-4000:]}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
