#!/bin/bash
cd "$(dirname "$0")/app" || exit 1
echo "========================================================"
echo "Starting PackSentry Backend Server..."
echo "OpenCV windows will pop up on your desktop!"
echo "========================================================"
python3 -m uvicorn main:app --port 8000 --reload
