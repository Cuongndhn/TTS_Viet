@echo off
REM =====================================================================
REM  VieNeu TTS Web - Script chay nhanh tren Windows
REM  Double-click file nay de mo web http://127.0.0.1:8000
REM =====================================================================
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] Kiem tra Python...
python --version || (echo Chua cai Python! Tai tai https://www.python.org/downloads/ & pause & exit /b 1)

echo [2/3] Cai thu vien thieu (neu co)...
python -m pip install --upgrade pip >nul 2>&1
if exist requirements.txt (
  python -m pip install -r requirements.txt
)

echo [3/3] Mo web TTS...
echo Mo trinh duyet: http://127.0.0.1:8000
python app.py
pause
