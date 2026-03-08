@echo off
REM Project Gorgon VIP Quest Helper - Windows Startup Script

echo ========================================
echo Project Gorgon VIP Quest Helper
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if Flask is installed, install if needed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo Starting Quest Helper...
echo.
echo Open your browser to: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the web server
python web_server.py

pause
