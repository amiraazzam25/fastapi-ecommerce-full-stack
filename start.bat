@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "%USERPROFILE%\AppData\Local\anaconda3\python.exe" set "PYTHON_EXE=%USERPROFILE%\AppData\Local\anaconda3\python.exe"

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if errorlevel 1 (
    start "Backend FastAPI" /D "%~dp0main_app" "%PYTHON_EXE%" -m uvicorn main:app --host 127.0.0.1 --port 8000
    timeout /t 3 /nobreak >nul
)

netstat -ano | findstr /R /C:":5500 .*LISTENING" >nul
if errorlevel 1 (
    start "Frontend FastAPI" /D "%~dp0" "%PYTHON_EXE%" frontend\dev-server.py --port 5500 --backend http://127.0.0.1:8000
    timeout /t 3 /nobreak >nul
)

set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"

if exist "%CHROME_EXE%" (
    start "" "%CHROME_EXE%" "http://127.0.0.1:5500/home"
) else (
    start "" "http://127.0.0.1:5500/home"
)
