#!/usr/bin/env bash
set -e

# 1. create / activate venv (cached in the image layer)
# if [ ! -d /opt/venv ]; then
#   python3.12 -m venv /opt/venv
# fi
# source /opt/venv/bin/activate

# 2. run FastAPI service
#exec uvicorn service:app --host 0.0.0.0 --port 8000

APP_MODULE="${APP_MODULE:-main:app}"

exec uvicorn "$APP_MODULE" --host 0.0.0.0 --port 8000
