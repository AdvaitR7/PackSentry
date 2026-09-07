#!/bin/bash
cd "$(dirname "$0")" || exit 1
echo "========================================================"
echo "Starting PackSentry Legal Metrology Backend Server..."
echo "API live on http://127.0.0.1:8000 (docs: /docs, health: /healthz)"
echo "========================================================"
export PYTHONPATH="..:.:$PYTHONPATH"
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
