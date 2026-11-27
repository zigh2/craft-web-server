@echo off
cd /d "%~dp0"
python server.py --setup-https %*
pause
