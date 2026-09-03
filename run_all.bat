@echo off
echo ===================================================
echo   Launching PackSentry Backend and Flutter App
echo ===================================================

:: Start Backend in a separate window
start "PackSentry Backend" cmd /k "cd /d ""%~dp0Backend\app"" && python -m uvicorn main:app --port 8000 --reload"

:: Start Flutter Web in Chrome in a separate window
start "PackSentry Flutter (Chrome)" cmd /k "cd /d ""%~dp0Frontend\app"" && flutter run -d chrome"
