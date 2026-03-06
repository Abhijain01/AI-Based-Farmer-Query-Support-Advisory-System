@echo off
echo ===================================================
echo   Starting Optimized Backend (Memory Safe Mode)
echo ===================================================
echo.
echo Stopping any running python processes (optional)...
taskkill /IM python.exe /F 2>nul
echo.
echo Activating virtual environment...
call venv\Scripts\activate
echo.
echo Launching app.py...
python app.py
pause
