# 🔍 Monitor Bańki AI

Prosty monitor sygnałów ostrzegawczych w branży AI.
Działa jako strona + aplikacja mobilna. **Dane odświeżają się automatycznie.**

---

## Szybki start na GitHub Pages

### 1. Utwórz repozytorium
- Wejdź na github.com → New repository
- Nazwa np. `monitor-banki-ai`
- Ustaw Public
- Create repository

### 2. Wgraj wszystkie pliki
Przeciągnij **całą zawartość** tego folderu
(w tym ukryty folder `.github`) i zrób Commit changes.

### 3. Włącz GitHub Pages
Settings → Pages → Source: branch `main`, folder `/ (root)` → Save

Strona będzie pod adresem:
https://TWOJA_NAZWA.github.io/monitor-banki-ai/

### 4. Włącz automatyczne aktualizacje (najważniejsze!)
1. Wejdź w zakładkę **Actions** w repozytorium
2. Jeśli GitHub pyta – kliknij „I understand my workflows, go ahead and enable them”
3. Po lewej wybierz workflow: **Aktualizuj dane Monitora Bańki AI**
4. Kliknij **Run workflow** → zielony przycisk **Run workflow**

Od tej pory dane aktualizują się **same co 6 godzin**.
W każdej chwili możesz też kliknąć Run workflow, żeby odświeżyć od razu.

---

## Aplikacja na telefon

Gdy strona już działa:

- Android (Chrome): menu → „Zainstaluj aplikację”
- iPhone (Safari): Udostępnij → „Dodaj do ekranu początkowego”

---

## Kolory

- 🟢 Zielony = spokój
- 🟡 Żółty = uważaj, obserwuj
- 🔴 Czerwony = mocny sygnał ostrzegawczy

---

## Jak to działa

GitHub Actions (darmowe):
1. Co 6 godzin uruchamia skrypt
2. Skrypt pobiera notowania, ceny GPU i dokumenty firm
3. Zapisuje wynik do monitor_data/latest_report.json
4. Twoja strona i apka na telefonie od razu widzą nowe dane

Nie musisz nic robić ręcznie ani pytać nikogo o raport.

---

To nie jest porada inwestycyjna.
