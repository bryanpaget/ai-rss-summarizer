@echo off
REM Auto-installer for RSS Summarizer (Windows)

echo.
echo === RSS Summarizer Installer ===
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check if pipx is available, install if not
pipx --version >nul 2>&1
if errorlevel 1 (
    echo pipx not found. Installing pipx...
    pip install pipx
    if errorlevel 1 (
        echo ERROR: Failed to install pipx.
        pause
        exit /b 1
    )
)

echo Installing RSS Summarizer...
pipx install "%~dp0."

if errorlevel 1 (
    echo.
    echo If you see "already installed", run: pipx reinstall rss-summarizer
    pause
    exit /b 1
)

echo.
echo =====================================================
echo SUCCESS! RSS Summarizer installed.
echo.
echo Commands:
echo   rss help        Show all commands
echo   rss setup       Configure your LLM provider
echo   rss update      Fetch and summarize new articles
echo =====================================================
pause
