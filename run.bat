@echo off
REM ============================================================
REM Starts the FastAPI backend using the project's .venv.
REM Run setup.bat first if you haven't already.
REM ============================================================

setlocal

set ROOT=%~dp0
set VENV_DIR=%ROOT%.venv
set BACKEND_DIR=%ROOT%backend

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [run] .venv not found. Please run setup.bat first.
    exit /b 1
)

pushd "%BACKEND_DIR%"
"%VENV_DIR%\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
popd

endlocal
