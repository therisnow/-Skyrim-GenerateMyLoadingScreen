@echo off
setlocal
cd /d "%~dp0"

echo Running Generate My Loading Screen...
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python GenerateMyLoadingScreen_ESL.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3 GenerateMyLoadingScreen_ESL.py
    ) else (
        echo ERROR: Python was not found.
        echo Please install Python 3 and enable "Add Python to PATH".
        pause
        exit /b 1
    )
)

pause
