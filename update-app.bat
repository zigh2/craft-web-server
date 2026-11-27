@echo off
title Craft Apps Release Manager
cd /d "%~dp0"
python updater.py %*
pause
