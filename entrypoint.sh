#!/usr/bin/env bash
set -e

# 1. create / activate venv (cached in the image layer)
if [ ! -d /opt/venv ]; then
  python3.12 -m venv /opt/venv
  /opt/venv/bin/pip install --upgrade pip
  /opt/venv/bin/pip install -r /tmp/requirements.txt
  /opt/venv/bin/pip install -e /opt/kai
fi
source /opt/venv/bin/activate

# 2. run FastAPI service
exec uvicorn service:app --host 0.0.0.0 --port 8000
