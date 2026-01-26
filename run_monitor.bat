@echo off
REM Script para activar el venv y lanzar el monitor/dashboard/clean plug-and-play (solo python)
cd /d %~dp0
call .venv\Scripts\activate.bat
if "%1"=="" (
    echo Uso: run_monitor.bat [monitor|dashboard|clean]
    exit /b 1
)
python -m src.main %*
