@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
)

.venv\Scripts\python.exe -c "import pygame" >nul 2>&1
if errorlevel 1 (
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

.venv\Scripts\python.exe -m pip install -e . --no-deps >nul
.venv\Scripts\python.exe -m lab_panic.main

if errorlevel 1 pause
endlocal
