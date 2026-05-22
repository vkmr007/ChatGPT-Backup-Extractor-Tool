@echo off
title Building ChatGPT Export Extractor EXE...
echo.
echo ================================================
echo   ChatGPT Export Extractor - EXE Builder
echo ================================================
echo.

:: Use the known Python path
set PYTHON=C:\Users\Lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe

if not exist "%PYTHON%" (
    echo ERROR: Python not found at expected path.
    echo Please update the PYTHON variable in this script.
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller and dependencies...
"%PYTHON%" -m pip install pyinstaller python-docx --quiet
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Building EXE with PyInstaller...
"%PYTHON%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "ChatGPT_Extractor" ^
    --add-data "extractor_core.py;." ^
    chatgpt_extractor.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo ================================================
echo   EXE created at:
echo   dist\ChatGPT_Extractor.exe
echo ================================================
echo.
echo Double-click dist\ChatGPT_Extractor.exe to run.
echo.
pause
