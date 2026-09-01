#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lokaler Server für den Anime-Synchro-Tracker.

Startet einen kleinen Flask-Server, liefert das HTML-Frontend aus und hält die
Anime-Daten im Speicher. Die Scraping- und Datenlogik kommt aus
anisearch_scraper.py – dieselbe, die auch GitHub Actions verwendet, damit es
nur eine Wahrheit über die Daten gibt.

Starten:  python scrape_anisearch_fixed.py
Windows:  Doppelklick auf "SERVER STARTEN.bat"
"""

import os
import sys
import threading
import time

from flask import Flask, jsonify, send_from_directory

from anisearch_scraper import (
    BASE_DIR,
    CATEGORY_ORDER,
    DATA_FILE,
    HTML_FILE,
    dedupe_categories,
    load_existing,
    print_summary,
    scrape_all,
    write_if_changed,
)

app = Flask(__name__)

AUTO_REFRESH_HOURS = 6

# Aktueller Datenstand im Speicher. Immer ein vollständiges Payload-Dict im
# selben Format wie anime_data.json – so liefern API und Datei exakt dasselbe.
STATE = {
    "payload": None,
    "scraping": False,
}
STATE_LOCK = threading.Lock()


def ensure_dependencies() -> None:
    """Fehlende Pakete nachinstallieren (Komfort für den Doppelklick-Start)."""
    missing = []
    for module, package in (("flask", "flask"), ("playwright", "playwright")):
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"📦 Installiere fehlende Pakete: {', '.join(missing)}")
        os.system(f'"{sys.executable}" -m pip install {" ".join(missing)} -q')

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception:
        print("📦 Installiere Playwright-Chromium...")
        os.system(f'"{sys.executable}" -m playwright install chromium')


def load_cache_into_state() -> bool:
    """Gespeicherte Daten in den Speicher laden, damit der Server sofort liefert."""
    data = load_existing(DATA_FILE)
    if not any(data.get(name) for name in CATEGORY_ORDER):
        return False
    with STATE_LOCK:
        STATE["payload"] = data
    total = sum(len(data.get(name, [])) for name in CATEGORY_ORDER)
    print(f"💾 {total} Anime aus {os.path.basename(DATA_FILE)} geladen (Stand: {data.get('timestamp')})")
    return True


def run_scraper() -> None:
    """Einmal komplett scrapen, entdoppeln und – nur bei Änderung – speichern."""
    from playwright.sync_api import sync_playwright

    with STATE_LOCK:
        if STATE["scraping"]:
            print("⚠️  Scraper läuft bereits – übersprungen")
            return
        STATE["scraping"] = True

    try:
        print("\n" + "=" * 60)
        print("🎬 ANISEARCH SCRAPER – Deutsche Synchronisationen")
        print("=" * 60)

        with sync_playwright() as pw:
            raw = scrape_all(pw)

        categories, warnings = dedupe_categories(raw)
        written, payload = write_if_changed(categories, warnings=warnings, path=DATA_FILE)

        with STATE_LOCK:
            STATE["payload"] = payload

        print_summary(payload, written, DATA_FILE)
    except Exception as e:
        print(f"❌ Scraper-Fehler: {e}")
    finally:
        with STATE_LOCK:
            STATE["scraping"] = False


def auto_refresh_loop(interval_hours: int = AUTO_REFRESH_HOURS) -> None:
    while True:
        time.sleep(interval_hours * 3600)
        print(f"\n🔄 Auto-Refresh (alle {interval_hours}h)...")
        run_scraper()


# ─── Flask-Endpunkte ──────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "HTML-Datei nicht gefunden!", 404


@app.route("/api/anime-data")
def api_anime_data():
    """Liefert den aktuellen Datenstand – identisches Format wie anime_data.json."""
    with STATE_LOCK:
        payload = STATE["payload"]
        scraping = STATE["scraping"]

    if payload:
        response = dict(payload)
        response["scraping"] = scraping
        response["source"] = "live"
        return jsonify(response)

    return jsonify({
        "error": "Noch keine Daten – Scraping läuft...",
        "scraping": scraping,
    }), 503


@app.route("/api/refresh")
def api_refresh():
    with STATE_LOCK:
        if STATE["scraping"]:
            return jsonify({"status": "Scraping läuft bereits...", "scraping": True})
    threading.Thread(target=run_scraper, daemon=True).start()
    return jsonify({"status": "Scraping gestartet...", "scraping": True})


@app.route("/api/status")
def api_status():
    with STATE_LOCK:
        payload = STATE["payload"] or {}
        scraping = STATE["scraping"]
    return jsonify({
        "status": "online",
        "counts": payload.get("counts", {name: 0 for name in CATEGORY_ORDER}),
        "total": payload.get("total", 0),
        "timestamp": payload.get("timestamp"),
        "warnings": payload.get("warnings", []),
        "scraping": scraping,
        "version": payload.get("version"),
    })


@app.route("/anime_data.json")
def serve_json():
    if os.path.exists(DATA_FILE):
        return send_from_directory(BASE_DIR, os.path.basename(DATA_FILE))
    return jsonify({"error": "Keine Datei"}), 404


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ─── Hauptprogramm ────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("🎬 ANIME SYNCHRO TRACKER – SERVER")
    print("=" * 60)
    print("\nAbhängigkeiten werden geprüft...")
    ensure_dependencies()

    print("\n1. [Scraper + Server] Scrapt anisearch.de & startet den Server")
    print("2. [Nur Server]       Startet den Server mit gespeicherten Daten")
    print("3. [Nur Scraper]      Scrapt anisearch.de, kein Server\n")

    choice = (input("Auswahl (1/2/3) [Standard: 1]: ").strip() or "1")

    if choice == "3":
        run_scraper()
        return

    load_cache_into_state()

    if choice != "2":
        print("\n📥 Starte Scraping im Hintergrund...")
        threading.Thread(target=run_scraper, daemon=True).start()
        threading.Thread(target=auto_refresh_loop, args=(AUTO_REFRESH_HOURS,), daemon=True).start()

    print("\n" + "=" * 60)
    print("🚀 Server:  http://localhost:5000")
    print("📡 API:     http://localhost:5000/api/anime-data")
    print("🔄 Refresh: http://localhost:5000/api/refresh")
    print("📊 Status:  http://localhost:5000/api/status")
    print("🛑 Beenden: CTRL+C")
    print("=" * 60 + "\n")

    try:
        app.run(debug=False, host="localhost", port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n✅ Server beendet.")


if __name__ == "__main__":
    main()
