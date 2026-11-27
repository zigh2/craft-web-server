@echo off
cd /d "%~dp0"
python server.py --set-admin-password
pause
