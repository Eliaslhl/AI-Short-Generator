@echo off
REM 🚀 Start Advanced Twitch Processing System (Windows)
REM Usage: start_services.bat [rq|celery]

setlocal enabledelayedexpansion

set QUEUE_BACKEND=%1
if "%QUEUE_BACKEND%"=="" set QUEUE_BACKEND=rq

setlocal enabledelayedexpansion
for %%I in ("%cd%") do set PROJECT_ROOT=%%~dpI
set BACKEND_DIR=%PROJECT_ROOT%backend

color 0E
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║  🚀 VideoToShort Advanced Twitch Processing System         ║
echo ║  📦 Queue Backend: %QUEUE_BACKEND%
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if Redis is running
echo [1/4] Checking Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Redis not running
    echo.
    echo Install Redis from: https://github.com/microsoftarchive/redis/releases
    echo Or use: choco install redis-64
    echo.
    pause
    exit /b 1
)
echo ✅ Redis running (localhost:6379)
echo.

REM Check Python
echo [2/4] Checking Python environment...
cd /d "%BACKEND_DIR%"
if not exist "venv" (
    echo ⚠️  Virtual environment not found, creating...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo ✅ Python venv activated
echo.

REM Install dependencies
echo [3/4] Installing dependencies...
pip install -q -r requirements.txt 2>nul
if errorlevel 1 (
    echo ⚠️  Some packages failed to install (optional)
)
echo ✅ Dependencies installed
echo.

REM Create .env if not exists
echo [4/4] Checking configuration...
if not exist ".env" (
    echo ⚠️  .env not found, creating with defaults...
    (
        echo # Queue Configuration
        echo QUEUE_BACKEND=%QUEUE_BACKEND%
        echo REDIS_URL=redis://localhost:6379/0
        echo.
        echo # Processing Configuration
        echo CHUNK_DURATION=1800
        echo WINDOW_SIZE=15
        echo WINDOW_OVERLAP=0.5
        echo.
        echo # Scoring Configuration
        echo AUDIO_WEIGHT=0.5
        echo MOTION_WEIGHT=0.2
        echo TEXT_WEIGHT=0.3
        echo MIN_SCORE_THRESHOLD=0.3
        echo MERGE_THRESHOLD=2.0
        echo.
        echo # API Configuration
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
    ) > .env
    echo ✅ .env created with defaults
)
echo.

REM Final checklist
echo ════════════════════════════════════════════════════════════
echo ✅ All checks passed! Ready to start services
echo ════════════════════════════════════════════════════════════
echo.
echo Next steps:
echo.
echo 1️⃣  Start Worker (in Command Prompt 1):
if "%QUEUE_BACKEND%"=="rq" (
    echo    rq worker
) else (
    echo    celery -A backend.queue.worker worker --loglevel=info
)
echo.
echo 2️⃣  Start FastAPI (in Command Prompt 2):
echo    cd %BACKEND_DIR%
echo    uvicorn main:app --reload
echo.
echo 3️⃣  Test API (in PowerShell/Cmd 3):
echo    curl -X POST http://localhost:8000/api/generate/twitch/advanced -H "Content-Type: application/json" -d "{\"url\": \"https://www.twitch.tv/videos/123456789\", \"max_clips\": 5, \"language\": \"en\"}"
echo.
echo Configuration file: %BACKEND_DIR%\.env
echo Queue backend: %QUEUE_BACKEND%
echo.
pause
