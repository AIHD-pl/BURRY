@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ==========================================
echo   🔍  MONITOR BAŃKI AI
echo ==========================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Nie znaleziono Pythona.
    echo Zainstaluj Python 3 ze strony: https://www.python.org/downloads/
    echo Zaznacz opcje "Add Python to PATH" podczas instalacji.
    echo.
    pause
    exit /b 1
)

echo - Sprawdzam potrzebne biblioteki...
python -m pip install -r requirements.txt -q

echo - Uruchamiam sprawdzanie danych...
echo.
python ai_bubble_monitor.py

echo.
echo ==========================================
echo   Dane zostaly zebrane.
echo   Otwieram dashboard w przegladarce...
echo ==========================================
echo.
echo   Adres: http://localhost:8000/dashboard.html
echo   Aby zatrzymac serwer – zamknij to okno
echo.

start http://localhost:8000/dashboard.html
python -m http.server 8000

pause
