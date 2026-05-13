@echo off
REM Scheduled runner for Windows Task Scheduler
REM Usage: Schedule this .bat file to run weekly/monthly

set PROJECT_DIR=%~dp0..

echo [%date% %time%] Starting scheduled DWH update >> "%PROJECT_DIR%\logs\scheduler.log"

cd /d "%PROJECT_DIR%"

REM Activate virtual environment and run
call .venv\Scripts\python.exe scripts\scheduled_run.py --weeks 2 >> "%PROJECT_DIR%\logs\scheduler.log" 2>&1

echo [%date% %time%] Scheduled run finished >> "%PROJECT_DIR%\logs\scheduler.log"
echo. >> "%PROJECT_DIR%\logs\scheduler.log"
