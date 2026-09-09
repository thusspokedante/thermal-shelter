@echo off
REM ============================================================
REM First-time setup for the thermal-shelter backend.
REM Creates .venv (at project root, outside backend/), installs
REM dependencies, and seeds the SQLite material database.
REM Safe to re-run: it will not recreate an existing .venv and
REM will not duplicate materials in an already-seeded database.
REM ============================================================

setlocal

set ROOT=%~dp0
set VENV_DIR=%ROOT%.venv
set BACKEND_DIR=%ROOT%backend

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo [setup] .venv already exists, skipping creation.
) else (
    echo [setup] Creating virtual environment at %VENV_DIR% ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [setup] ERROR: failed to create virtual environment. Is Python installed and on PATH?
        exit /b 1
    )
)

echo [setup] Installing backend dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 (
    echo [setup] ERROR: dependency installation failed.
    exit /b 1
)

echo [setup] Initializing/seeding the material database...
pushd "%BACKEND_DIR%"
"%VENV_DIR%\Scripts\python.exe" seed_db.py
if errorlevel 1 (
    echo [setup] ERROR: database seeding failed.
    popd
    exit /b 1
)
popd

echo.
echo [setup] Done. Start the backend with: run.bat
endlocal
