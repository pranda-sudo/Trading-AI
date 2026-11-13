@echo off
cd /d "%~dp0"
set "TRADING_AI_MT5_PATH=C:\AItrading\petr\terminal64.exe"
set "TRADING_AI_MT5_LOGIN=68531109"
set "TRADING_AI_INTERVAL_SECONDS=60"
py -3.11 collector.py
pause
