@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" library_app.py --host 127.0.0.1 --port 8010
) else (
    python library_app.py --host 127.0.0.1 --port 8010
)

