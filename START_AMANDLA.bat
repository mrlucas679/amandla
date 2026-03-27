@echo off
title AMANDLA Launcher
color 0A

echo.
echo  ============================================
echo    AMANDLA - Sign Language Bridge
echo  ============================================
echo.

:: Check if Ollama is already running
curl -s http://localhost:11434 >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Ollama is already running.
) else (
    echo  [..] Starting Ollama...
    start "Ollama" /min ollama serve
    echo  [..] Waiting for Ollama to be ready...
    :wait_ollama
    timeout /t 2 /nobreak >nul
    curl -s http://localhost:11434 >nul 2>&1
    if %errorlevel% neq 0 goto wait_ollama
    echo  [OK] Ollama is ready.
)

echo.
echo  [..] Starting AMANDLA...
echo.

npm start

pause