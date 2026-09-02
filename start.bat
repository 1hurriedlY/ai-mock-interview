@echo off
chcp 65001 >nul
title Mock Interview AI - Launcher
cd /d "%~dp0"

echo ==========================================
echo   Mock Interview AI - Project Launcher
echo ==========================================
echo.

rem ---- 1. Check MySQL(3306) and Redis(6379) ----
netstat -ano | findstr LISTENING | findstr /C:":3306 " >nul 2>&1
if not errorlevel 1 goto mysql_ok
echo [ERROR] MySQL is not running on port 3306.
echo         Please start MySQL first, then run this script again.
echo.
pause
exit /b 1
:mysql_ok

netstat -ano | findstr LISTENING | findstr /C:":6379 " >nul 2>&1
if not errorlevel 1 goto redis_ok
echo [ERROR] Redis is not running on port 6379.
echo         Please start Redis first, then run this script again.
echo.
pause
exit /b 1
:redis_ok
echo [1/3] Env check passed: MySQL and Redis are running.
echo.

rem ---- 2. Start backend (port 8000) ----
echo [2/3] Checking backend on port 8000 ...
netstat -ano | findstr LISTENING | findstr /C:":8000 " >nul 2>&1
if not errorlevel 1 goto backend_running
echo        Starting backend in a new window ...
start "interview-backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend"
goto backend_done
:backend_running
echo        Backend is already running, skipped.
:backend_done
echo.

rem ---- 3. Start frontend (port 5173) ----
echo [3/3] Checking frontend on port 5173 ...
netstat -ano | findstr LISTENING | findstr /C:":5173 " >nul 2>&1
if not errorlevel 1 goto frontend_running
echo        Starting frontend in a new window ...
start "interview-frontend" cmd /k "cd /d %~dp0interview-frontend && npm run dev"
goto frontend_done
:frontend_running
echo        Frontend is already running, skipped.
:frontend_done
echo.

rem ---- Open browser ----
echo Waiting for services to be ready ...
timeout /t 8 /nobreak >nul
start "" http://localhost:5173

echo.
echo Done.
echo   Backend : http://localhost:8000   (window: interview-backend)
echo   Frontend: http://localhost:5173   (window: interview-frontend)
echo.
echo Tips:
echo   - Close a window to stop that service.
echo   - You may close this window now.
echo.
pause
