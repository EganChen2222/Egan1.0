@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "%~dp0app.py"
    exit /b
)
python -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo Python or PySide6 is missing. See README.md for setup.
    pause
    exit /b 1
)
for /f "delims=" %%P in ('python -c "import sys; from pathlib import Path; print(Path(sys.executable).with_name('pythonw.exe'))"') do set "TODO_PYTHONW=%%P"
if exist "%TODO_PYTHONW%" (
    start "" "%TODO_PYTHONW%" "%~dp0app.py"
) else (
    python "%~dp0app.py"
)
