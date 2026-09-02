#!/usr/bin/env python3
"""
Prosty kreator powiadomień na telefon (Telegram)
===============================================
Uruchom ten plik, a przeprowadzi Cię krok po kroku.
"""

import re
from pathlib import Path

def main():
    print()
    print("=" * 55)
    print("  📱  POWIADOMIENIA NA TELEFON (Telegram)")
    print("=" * 55)
    print()
    print("Dzięki temu dostaniesz SMS-a (przez Telegram),")
    print("gdy monitor wykryje coś niepokojącego.")
    print()
    print("Krok 1: Zainstaluj aplikację Telegram na telefonie")
    print("        (jeśli jeszcze nie masz).")
    print()
    print("Krok 2: W Telegramie wyszukaj: @BotFather")
    print("        Napisz do niego: /newbot")
    print("        Podążaj za instrukcjami i wymyśl nazwę bota.")
    print()
    print("Krok 3: BotFather da Ci TOKEN (długi kod).")
    print("        Skopiuj go.")
    print()
    
    token = input("Wklej tutaj TOKEN od BotFather: ").strip()
    if not token or ":" not in token:
        print("To nie wygląda na prawidłowy token. Spróbuj ponownie.")
        return

    print()
    print("Krok 4: Teraz napisz coś do swojego nowego bota")
    print("        (wyszukaj go po nazwie, którą wymyśliłeś).")
    print("        Po prostu wyślij mu dowolną wiadomość, np. „cześć”.")
    print()
    input("Jak już napiszesz do bota – naciśnij Enter...")

    print()
    print("Krok 5: Pobieram Twój numer czatu...")
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        chat_id = None
        if data.get("ok") and data.get("result"):
            for update in reversed(data["result"]):
                if "message" in update:
                    chat_id = str(update["message"]["chat"]["id"])
                    break
        
        if not chat_id:
            print("Nie znalazłem wiadomości. Upewnij się, że napisałeś do bota,")
            print("i uruchom ten program jeszcze raz.")
            return
            
    except Exception as e:
        print(f"Błąd: {e}")
        print("Sprawdź połączenie z internetem i spróbuj ponownie.")
        return

    print(f"Znalazłem Chat ID: {chat_id}")
    print()

    # Zapisz do pliku konfiguracyjnego
    config_path = Path("telegram_config.txt")
    config_path.write_text(f"TELEGRAM_BOT_TOKEN={token}\nTELEGRAM_CHAT_ID={chat_id}\n", encoding="utf-8")

    # Podmień w głównym programie
    main_py = Path("ai_bubble_monitor.py")
    if main_py.exists():
        text = main_py.read_text(encoding="utf-8")
        text = re.sub(
            r'TELEGRAM_BOT_TOKEN = .*',
            f'TELEGRAM_BOT_TOKEN = "{token}"',
            text
        )
        text = re.sub(
            r'TELEGRAM_CHAT_ID = .*',
            f'TELEGRAM_CHAT_ID = "{chat_id}"',
            text
        )
        main_py.write_text(text, encoding="utf-8")
        print("✅ Ustawienia zapisane w programie głównym.")
    
    print()
    print("Wysyłam wiadomość testową...")
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "✅ Monitor Bańki AI – powiadomienia działają!"},
            timeout=10
        )
        print("Wiadomość wysłana! Sprawdź telefon.")
    except Exception as e:
        print(f"Nie udało się wysłać testu: {e}")

    print()
    print("=" * 55)
    print("  Gotowe! Od teraz alerty będą przychodzić na Telegram.")
    print("=" * 55)
    print()

if __name__ == "__main__":
    main()
