@echo off
setlocal
cd /d "%~dp0\.."
where python >nul 2>&1 || (echo Python not found & exit /b 1)
python -m pip install --quiet -r requirements.txt
python tools\build_all.py
if errorlevel 1 (echo BUILD FAILED & exit /b 1)
echo BUILD OK
endlocal
