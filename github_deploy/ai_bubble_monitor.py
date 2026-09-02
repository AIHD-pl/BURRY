#!/usr/bin/env python3
"""
AI Bubble & GPU Depreciation Monitor v2
=======================================
Zaawansowany monitor kluczowych wskaźników związanych z bańką AI
i kreatywną księgowością amortyzacji GPU.

Funkcje:
- Monitoring filingów SEC (10-K, 10-Q, 8-K) pod kątem zmian useful life
- Śledzenie cen GPU (rynku wtórnego / wynajmu)
- Analiza akcji (NVDA, META, MSFT, GOOGL, AMZN, ORCL, SOXX)
- Wykrywanie anomalii wolumenu i cen
- Alerty (konsola + opcjonalnie Telegram)
- Zapisywanie historii i snapshotów
- Prosty raport dzienny

Autor: Grok AI Assistant
Data: 2026-09
"""

import requests
import yfinance as yf
import pandas as pd
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

# ============================================================
# KONFIGURACJA
# ============================================================

class Config:
    # Firmy do monitorowania
    TICKERS = ["NVDA", "META", "MSFT", "GOOGL", "AMZN", "ORCL", "SOXX", "MU"]
    
    SEC_COMPANIES = {
        "META":  "0001326801",
        "MSFT":  "0000789019",
        "GOOGL": "0001652044",
        "AMZN":  "0001018724",
        "ORCL":  "0001341439",
        "NVDA":  "0001045810",
        "MU":    "0000723125",
    }
    
    # Słowa kluczowe do wykrywania zmian księgowych
    DEPRECIATION_KEYWORDS = [
        r"useful\s+life",
        r"estimated\s+useful\s+lives",
        r"change\s+in\s+estimate",
        r"accelerated\s+depreciation",
        r"impairment\s+(?:of\s+)?(?:long-lived\s+)?assets?",
        r"write[- ]?down",
        r"write[- ]?off",
        r"server(?:s)?\s+(?:and\s+)?network(?:ing)?\s+assets?",
        r"depreciation\s+(?:period|schedule|expense)",
        r"extended?\s+(?:the\s+)?(?:estimated\s+)?useful\s+life",
        r"shortened?\s+(?:the\s+)?(?:estimated\s+)?useful\s+life",
        r"revised\s+(?:the\s+)?estimated\s+useful\s+lives?",
    ]
    
    # Progi alertów
    GPU_PRICE_DROP_PCT = 12.0       # % spadku ceny GPU (dzień do dnia / tydzień)
    STOCK_MOVE_PCT = 7.0            # % ruchu dziennego akcji
    VOLUME_SPIKE_RATIO = 2.2        # wielokrotność średniego wolumenu
    SEC_LOOKBACK_DAYS = 21          # ile dni wstecz sprawdzać filingi
    
    # Ścieżki
    DATA_DIR = Path("monitor_data")
    HISTORY_FILE = DATA_DIR / "history.json"
    ALERTS_LOG = DATA_DIR / "alerts.log"
    STATE_FILE = DATA_DIR / "state.json"
    
    # SEC
    SEC_HEADERS = {
        "User-Agent": "AI-Bubble-Monitor research@personal-use.com",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }
    
    # Opcjonalnie: Telegram (uzupełnij token i chat_id)
    TELEGRAM_BOT_TOKEN = None       # np. "123456:ABC-DEF..."
    TELEGRAM_CHAT_ID = None         # np. "123456789"
    
    # Interwał (w sekundach) przy pracy w pętli
    LOOP_INTERVAL = 4 * 3600        # 4 godziny


# ============================================================
# LOGOWANIE
# ============================================================

def setup_logging():
    Config.DATA_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Config.DATA_DIR / "monitor.log", encoding="utf-8")
        ]
    )
    return logging.getLogger("AIMonitor")


log = setup_logging()


# ============================================================
# POMOCNICZE
# ============================================================

def load_json(path: Path, default=None):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def save_json(path: Path, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def send_telegram(message: str):
    """Wysyła alert na Telegram (jeśli skonfigurowano)"""
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": Config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log.warning(f"Nie udało się wysłać wiadomości Telegram: {e}")


def alert(message: str, level: str = "WARNING"):
    """Loguje i (opcjonalnie) wysyła alert"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{level}] {message}"
    
    if level == "CRITICAL":
        log.critical(message)
    else:
        log.warning(message)
    
    # Zapis do pliku alertów
    with open(Config.ALERTS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {full_msg}\n")
    
    # Telegram
    emoji = "🚨" if level == "CRITICAL" else "⚠️"
    send_telegram(f"{emoji} <b>AI Monitor</b>\n{message}")


# ============================================================
# MODUŁ: SEC FILINGS
# ============================================================

class SECMonitor:
    def __init__(self):
        self.state = load_json(Config.STATE_FILE, {"seen_filings": {}})
    
    def get_recent_filings(self, cik: str, days: int = None) -> List[Dict]:
        days = days or Config.SEC_LOOKBACK_DAYS
        url = f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"
        
        try:
            r = requests.get(url, headers=Config.SEC_HEADERS, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.error(f"SEC request failed for CIK {cik}: {e}")
            return []
        
        filings = []
        recent = data.get("filings", {}).get("recent", {})
        cutoff = datetime.now() - timedelta(days=days)
        
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])
        
        for i, form in enumerate(forms):
            try:
                fdate = datetime.strptime(dates[i], "%Y-%m-%d")
            except Exception:
                continue
                
            if fdate < cutoff:
                continue
                
            if form not in ["10-K", "10-Q", "8-K", "10-K/A", "10-Q/A", "8-K/A"]:
                continue
            
            filings.append({
                "form": form,
                "date": dates[i],
                "accession": accessions[i],
                "primary_doc": primary_docs[i],
                "description": descriptions[i] if i < len(descriptions) else "",
                "cik": cik
            })
        
        return filings
    
    def get_filing_text_url(self, cik: str, accession: str, primary_doc: str) -> str:
        acc_no = accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no}/{primary_doc}"
    
    def check_filing_content(self, url: str) -> List[str]:
        """Pobiera treść filingu i szuka słów kluczowych (prosta wersja)"""
        hits = []
        try:
            # SEC wymaga User-Agent
            headers = {
                "User-Agent": "AI-Bubble-Monitor research@personal-use.com",
                "Accept": "text/html,application/xhtml+xml"
            }
            r = requests.get(url, headers=headers, timeout=25)
            if r.status_code != 200:
                return hits
            
            text = r.text.lower()
            
            for pattern in Config.DEPRECIATION_KEYWORDS:
                if re.search(pattern, text, re.IGNORECASE):
                    hits.append(pattern)
            
        except Exception as e:
            log.debug(f"Nie udało się pobrać treści {url}: {e}")
        
        return list(set(hits))
    
    def scan_all(self) -> Dict[str, Any]:
        results = {}
        new_alerts = []
        
        for name, cik in Config.SEC_COMPANIES.items():
            log.info(f"Sprawdzam SEC filings: {name}")
            filings = self.get_recent_filings(cik)
            
            company_results = []
            seen = self.state["seen_filings"].setdefault(name, [])
            
            for f in filings:
                filing_id = f"{f['accession']}_{f['primary_doc']}"
                is_new = filing_id not in seen
                
                item = {
                    "form": f["form"],
                    "date": f["date"],
                    "url": self.get_filing_text_url(cik, f["accession"], f["primary_doc"]),
                    "is_new": is_new,
                    "keyword_hits": []
                }
                
                # Sprawdzamy treść tylko dla nowych lub ważnych formularzy
                if is_new or f["form"] in ["10-K", "10-Q"]:
                    hits = self.check_filing_content(item["url"])
                    item["keyword_hits"] = hits
                    
                    if hits and is_new:
                        msg = (f"SEC {name} | Nowy {f['form']} ({f['date']}) "
                               f"zawiera frazy związane z amortyzacją: {', '.join(hits[:3])}\n"
                               f"Link: {item['url']}")
                        alert(msg, level="CRITICAL")
                        new_alerts.append(msg)
                
                company_results.append(item)
                
                if is_new:
                    seen.append(filing_id)
            
            # Ograniczamy historię
            self.state["seen_filings"][name] = seen[-50:]
            results[name] = company_results
            
            time.sleep(0.3)  # szanujemy rate limit SEC
        
        save_json(Config.STATE_FILE, self.state)
        return {"filings": results, "alerts": new_alerts}


# ============================================================
# MODUŁ: CENY GPU
# ============================================================

class GPUPriceMonitor:
    def __init__(self):
        self.history = load_json(Config.HISTORY_FILE, {"gpu_prices": []})
    
    def fetch_ornnai(self) -> Dict[str, float]:
        prices = {}
        gpus = ["H100 SXM", "H200", "B200", "A100 SXM4"]
        
        for gpu in gpus:
            try:
                r = requests.get(
                    f"https://api.ornnai.com/api/gpu/{gpu}",
                    timeout=12
                )
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    val = data.get("index_value")
                    if val is not None:
                        prices[gpu] = float(val)
            except Exception as e:
                log.debug(f"OrnnAI {gpu}: {e}")
            time.sleep(0.2)
        
        return prices
    
    def fetch_gputable(self) -> Dict[str, float]:
        """Próba pobrania z gputable.dev (jeśli dostępne)"""
        prices = {}
        try:
            r = requests.get("https://gputable.dev/data.json", timeout=15)
            if r.status_code == 200:
                data = r.json()
                # Struktura może się zmieniać – elastyczne parsowanie
                if isinstance(data, list):
                    for item in data:
                        name = item.get("gpu") or item.get("name") or ""
                        price = item.get("price") or item.get("price_per_hour")
                        if name and price:
                            prices[str(name)] = float(price)
        except Exception as e:
            log.debug(f"GPUTable: {e}")
        return prices
    
    def get_current_prices(self) -> Dict[str, float]:
        prices = {}
        prices.update(self.fetch_ornnai())
        # prices.update(self.fetch_gputable())  # odkomentuj jeśli chcesz
        return prices
    
    def analyze(self) -> Dict[str, Any]:
        current = self.get_current_prices()
        log.info(f"Aktualne ceny GPU: {current}")
        
        # Porównanie z poprzednim snapshotem
        history = self.history.get("gpu_prices", [])
        alerts = []
        
        if history:
            last = history[-1].get("prices", {})
            for gpu, price in current.items():
                if gpu in last and last[gpu] > 0:
                    change_pct = ((price - last[gpu]) / last[gpu]) * 100
                    if change_pct <= -Config.GPU_PRICE_DROP_PCT:
                        msg = (f"GPU {gpu}: spadek o {change_pct:.1f}% "
                               f"({last[gpu]:.2f} → {price:.2f})")
                        alert(msg, level="CRITICAL")
                        alerts.append(msg)
        
        # Zapis do historii
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prices": current
        }
        history.append(entry)
        # Trzymamy ostatnie 200 wpisów
        self.history["gpu_prices"] = history[-200:]
        save_json(Config.HISTORY_FILE, self.history)
        
        return {
            "current": current,
            "alerts": alerts,
            "history_points": len(self.history["gpu_prices"])
        }


# ============================================================
# MODUŁ: AKCJE
# ============================================================

class StockMonitor:
    def get_data(self) -> Dict[str, Any]:
        results = {}
        alerts = []
        
        for ticker in Config.TICKERS:
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="10d")
                
                if len(hist) < 3:
                    continue
                
                last = hist.iloc[-1]
                prev = hist.iloc[-2]
                
                change_pct = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100
                avg_vol = hist["Volume"].iloc[:-1].mean()
                vol_ratio = last["Volume"] / avg_vol if avg_vol > 0 else 1.0
                
                # Trend 5-dniowy
                if len(hist) >= 6:
                    five_day_change = ((last["Close"] - hist.iloc[-6]["Close"]) / hist.iloc[-6]["Close"]) * 100
                else:
                    five_day_change = None
                
                item = {
                    "price": round(float(last["Close"]), 2),
                    "change_pct": round(change_pct, 2),
                    "volume_ratio": round(vol_ratio, 2),
                    "five_day_change_pct": round(five_day_change, 2) if five_day_change is not None else None,
                    "alert": False
                }
                
                # Warunki alertu
                reasons = []
                if abs(change_pct) >= Config.STOCK_MOVE_PCT:
                    reasons.append(f"ruch {change_pct:+.1f}%")
                if vol_ratio >= Config.VOLUME_SPIKE_RATIO:
                    reasons.append(f"wolumen {vol_ratio:.1f}x")
                
                if reasons:
                    item["alert"] = True
                    msg = f"{ticker}: {', '.join(reasons)} | Cena: ${item['price']}"
                    alert(msg)
                    alerts.append(msg)
                
                results[ticker] = item
                
            except Exception as e:
                log.error(f"Błąd przy {ticker}: {e}")
        
        return {"stocks": results, "alerts": alerts}


# ============================================================
# GŁÓWNY MONITOR
# ============================================================

class AIBubbleMonitor:
    def __init__(self):
        self.sec = SECMonitor()
        self.gpu = GPUPriceMonitor()
        self.stocks = StockMonitor()
    
    def run_once(self) -> Dict[str, Any]:
        # CI-friendly: zawsze mamy katalog na dane
        Config.DATA_DIR.mkdir(exist_ok=True)
        log.info("=" * 60)
        log.info("Uruchamiam pełny skan AI Bubble Monitor")
        log.info("=" * 60)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "stocks": {},
            "gpu": {},
            "sec": {},
            "all_alerts": []
        }
        
        # 1. Akcje
        log.info("→ Moduł akcji...")
        stock_data = self.stocks.get_data()
        report["stocks"] = stock_data.get("stocks", {})
        report["all_alerts"].extend(stock_data.get("alerts", []))
        
        # 2. Ceny GPU
        log.info("→ Moduł cen GPU...")
        gpu_data = self.gpu.analyze()
        report["gpu"] = gpu_data
        report["all_alerts"].extend(gpu_data.get("alerts", []))
        
        # 3. SEC
        log.info("→ Moduł SEC filings...")
        sec_data = self.sec.scan_all()
        report["sec"] = sec_data
        report["all_alerts"].extend(sec_data.get("alerts", []))
        
        # 4. Zapis pełnego raportu
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Config.DATA_DIR / f"report_{ts}.json"
        save_json(report_path, report)
        
        # Zawsze nadpisuj latest_report.json (dla dashboardu)
        latest_path = Config.DATA_DIR / "latest_report.json"
        save_json(latest_path, report)
        
        log.info(f"Raport zapisany: {report_path}")
        log.info(f"Latest report:  {latest_path}")
        
        # 5. Podsumowanie
        self.print_summary(report)
        
        return report
    
    def print_summary(self, report: Dict):
        """Przyjazne dla laika podsumowanie w konsoli"""
        alerts = report.get("all_alerts", [])
        num_alerts = len(alerts)

        print("\n")
        print("╔" + "═" * 58 + "╗")
        print("║" + "     🔍  MONITOR BAŃKI AI  –  PODSUMOWANIE DLA CIEBIE     ".center(58) + "║")
        print("╚" + "═" * 58 + "╝")
        print(f"   Czas sprawdzenia: {report['timestamp'][:19].replace('T', ' ')}")
        print()

        # Ocena ogólna
        if num_alerts == 0:
            print("   🟢  OCENA: SPOKOJNIE")
            print("   Nie wykryto żadnych mocnych sygnałów ostrzegawczych.")
        elif num_alerts <= 2:
            print("   🟡  OCENA: UWAŻAJ")
            print("   Pojawiły się pierwsze sygnały – warto obserwować.")
        else:
            print("   🔴  OCENA: MOCNY SYGNAŁ OSTRZEGAWCZY")
            print("   Wykryto kilka niepokojących rzeczy naraz.")
        print()

        # Akcje – prosto
        print("   📊  NOTOWANIA SPÓŁEK")
        print("   " + "-"*50)
        for ticker, data in report.get("stocks", {}).items():
            icon = "⚠️ " if data.get("alert") else "   "
            direction = "wzrosła" if data["change_pct"] > 0 else "spadła" if data["change_pct"] < 0 else "bez zmian"
            print(f"   {icon}{ticker:6}  ${data['price']:<8.0f}  {direction} o {abs(data['change_pct']):.1f}%")
        print()

        # GPU
        print("   🖥️   CENY KART GRAFICZNYCH (GPU)")
        print("   " + "-"*50)
        gpu_prices = report.get("gpu", {}).get("current", {})
        if gpu_prices:
            for name, price in gpu_prices.items():
                print(f"      {name:15}  →  {price:.2f}")
            if report.get("gpu", {}).get("alerts"):
                print("      ⚠️  Wykryto spadki cen – to ważny sygnał!")
            else:
                print("      Ceny wyglądają stabilnie.")
        else:
            print("      Brak danych o cenach.")
        print()

        # SEC
        print("   📄  DOKUMENTY FIRM (czy coś zmienili w księgowości?)")
        print("   " + "-"*50)
        found = False
        for company, filings in report.get("sec", {}).get("filings", {}).items():
            for f in filings:
                if f.get("keyword_hits") and f.get("is_new"):
                    found = True
                    print(f"      ⚠️  {company} zgłosił coś ważnego ({f['form']}, {f['date']})")
        if not found:
            print("      ✅  Nic nowego i niepokojącego w dokumentach firm.")
        print()

        # Alerty
        print("   🔔  ALERTY")
        print("   " + "-"*50)
        if not alerts:
            print("      Brak alertów – wszystko wygląda w porządku.")
        else:
            for a in alerts:
                print(f"      • {a}")
        print()
        print("   💡  Otwórz dashboard.html w przeglądarce, żeby zobaczyć")
        print("       ładniejszą, graficzną wersję tych informacji.")
        print("╔" + "═" * 58 + "╗")
        print("║" + "     Gotowe. Możesz zamknąć to okno lub uruchomić ponownie.     ".center(58) + "║")
        print("╚" + "═" * 58 + "╝")
        print()
    
    def run_loop(self):
        """Uruchamia monitor w pętli"""
        log.info(f"Start pętli monitorującej (interwał {Config.LOOP_INTERVAL // 3600}h)")
        while True:
            try:
                self.run_once()
            except Exception as e:
                log.exception(f"Błąd w cyklu monitora: {e}")
            
            log.info(f"Czekam {Config.LOOP_INTERVAL // 3600} godzin...")
            time.sleep(Config.LOOP_INTERVAL)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Bubble & GPU Depreciation Monitor")
    parser.add_argument("--loop", action="store_true", help="Uruchom w pętli")
    parser.add_argument("--once", action="store_true", help="Jednorazowy skan (domyślne)")
    args = parser.parse_args()
    
    monitor = AIBubbleMonitor()
    
    if args.loop:
        monitor.run_loop()
    else:
        monitor.run_once()
