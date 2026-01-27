@echo off
REM Script para activar el venv y lanzar el monitor/dashboard/clean plug-and-play (solo python)
cd /d %~dp0
call .venv\Scripts\activate.bat
if "%1"=="" (
    echo Uso: run_monitor.bat [monitor|dashboard|clean]
    exit /b 1
)
@echo off
REM Script multiplataforma para ejecutar el monitor, dashboard o limpieza
REM Uso: run_monitor.bat [monitor|dashboard|clean]

if "%1"=="" (
    echo Uso: %0 [monitor^|dashboard^|clean]
    exit /b 1
)

REM Detectar si uv.exe existe en el venv y usarlo si está disponible
set "UV_PATH=%~dp0.venv\Scripts\uv.exe"
if exist "%UV_PATH%" (
    "%UV_PATH%" run python -m src.main %*
    exit /b %ERRORLEVEL%
)

REM Si no, usar python normal
python -m src.main %*
