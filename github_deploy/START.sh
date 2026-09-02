#!/bin/bash
# ============================================
#  MONITOR BAŃKI AI – uruchomienie jednym kliknięciem
# ============================================

cd "$(dirname "$0")"

echo ""
echo "=========================================="
echo "  🔍  MONITOR BAŃKI AI"
echo "=========================================="
echo ""

# Sprawdź czy Python jest dostępny
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Nie znaleziono Pythona."
    echo "   Zainstaluj Python 3 ze strony: https://www.python.org/downloads/"
    echo ""
    read -p "Naciśnij Enter, aby zamknąć..."
    exit 1
fi

# Użyj python3 jeśli jest, inaczej python
PYTHON=python3
command -v python3 &> /dev/null || PYTHON=python

echo "→ Sprawdzam potrzebne biblioteki..."
$PYTHON -m pip install -r requirements.txt -q

echo "→ Uruchamiam sprawdzanie danych..."
echo ""
$PYTHON ai_bubble_monitor.py

echo ""
echo "=========================================="
echo "  Dane zostały zebrane."
echo "  Otwieram dashboard w przeglądarce..."
echo "=========================================="
echo ""
echo "  Adres: http://localhost:8000/dashboard.html"
echo "  Aby zatrzymać serwer – naciśnij Ctrl+C"
echo ""

# Otwórz przeglądarkę (działa na większości systemów)
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:8000/dashboard.html" &
elif command -v open &> /dev/null; then
    open "http://localhost:8000/dashboard.html" &
fi

$PYTHON -m http.server 8000
