@echo off
:: Job Application GUI Launcher for Windows
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: Set virtual environment path
if exist "%SCRIPT_DIR%venv_gui\Scripts\python.exe" (
    set PYTHON_EXE="%SCRIPT_DIR%venv_gui\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set PYTHON_EXE="%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    set PYTHON_EXE=python
)

echo Launching Job Application GUI...
echo Python: %PYTHON_EXE%

%PYTHON_EXE% app.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    pause
)
