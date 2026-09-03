@echo off
title LOCAL AI DESKTOP AGENT
color 07
cls
cd /d "%~dp0"
echo Starting Local AI Desktop Agent...
echo.
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred while running the agent.
    pause
)
