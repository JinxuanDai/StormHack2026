@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.13 -m venv .venv
    if errorlevel 1 py -3.12 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.22.3
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m PyInstaller --noconfirm "Lab Panic.spec"
if errorlevel 1 goto failed
echo Ready to share: dist\Lab Panic.exe
pause
exit /b 0
:failed
echo Build failed. Building requires Python 3.12 or 3.13; players do not need Python.
pause
exit /b 1
