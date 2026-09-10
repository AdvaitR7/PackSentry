#!/bin/bash
cd "$(dirname "$0")" || exit 1

# Auto-detect Python executable with uvicorn installed
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PY_BIN="$VIRTUAL_ENV/bin/python"
elif [ -x ".venv/bin/python" ]; then
    PY_BIN=".venv/bin/python"
elif [ -x "../Backend/.venv/bin/python" ]; then
    PY_BIN="../Backend/.venv/bin/python"
elif [ -x "/home/clandestine/.local/bin/python3.10" ]; then
    PY_BIN="/home/clandestine/.local/bin/python3.10"
elif command -v python3 >/dev/null 2>&1; then
    PY_BIN="$(command -v python3)"
else
    PY_BIN="python"
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "========================================================"
echo "Starting PackSentry Legal Metrology Backend Server..."
echo "Python binary: $PY_BIN ($($PY_BIN --version 2>&1))"
echo "API live on http://$HOST:$PORT (docs: /docs, health: /healthz)"
echo "========================================================"

export PYTHONPATH="..:.:$PYTHONPATH"
ENV_FILE_ARGS=()
if [ -f ".env" ]; then
    ENV_FILE_ARGS=(--env-file .env)
fi
exec "$PY_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload "${ENV_FILE_ARGS[@]}"
