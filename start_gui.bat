@echo off
title AI DESKTOP AGENT
cd /d "%~dp0"
python gui.py
if errorlevel 1 (
    pause
)
