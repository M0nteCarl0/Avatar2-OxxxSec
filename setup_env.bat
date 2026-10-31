@echo off
REM ==============================================================================
REM Avatar2 OxxxSec - Automated Virtual Environment Setup (Windows CMD)
REM ==============================================================================

echo =================================================================
echo   Avatar2 Master Playbook - Environment Setup (Windows CMD)
echo =================================================================

set "VENV_DIR=%~dp0.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [*] Creating virtual environment in .venv...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [-] Failed to create virtual environment!
        exit /b 1
    )
) else (
    echo [+] Virtual environment already exists.
)

echo [*] Upgrading pip, setuptools, and wheel...
"%PYTHON_EXE%" -m pip install --upgrade pip "setuptools<70" wheel

echo [*] Installing dependencies...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"

echo [*] Running verification suite...
"%PYTHON_EXE%" "%~dp0verify_all.py"

if errorlevel 1 (
    echo.
    echo [-] Verification failed! Please check the log output above.
    exit /b 1
)

echo.
echo [+] Environment setup completed successfully!
echo [*] Activate via: .venv\Scripts\activate.bat
