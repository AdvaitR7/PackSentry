@echo off
title PackSentry Backend (Interactive Desktop Mode)
cd /d "%~dp0\app"
echo ========================================================
echo Starting PackSentry Backend Server...
echo OpenCV windows will pop up on your desktop!
echo ========================================================
python -m uvicorn main:app --port 8000 --reload
pause
