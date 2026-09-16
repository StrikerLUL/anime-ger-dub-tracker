#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lokaler Server für den Anime Ger Dub Tracker.

Liefert das Frontend aus und hält die Daten im Speicher. Die Logik kommt aus
der Pipeline – dieselbe, die auch GitHub Actions verwendet, damit es nur eine
Wahrheit über die Daten gibt.

    python -m tracker serve
    python scrape_anisearch_fixed.py      (mit Menü)
    Windows: Doppelklick auf "SERVER STARTEN.bat"
"""

from __future__ import annotations

import os
import sys
import threading
import time

from .config import BASE_DIR, CATEGORY_ORDER, HTML_FILE, Settings
from .store import load

AUTO_REFRESH_HOURS = 6

#: Aktueller Stand im Speicher – immer ein vollständiges Payload-Dict im
#: selben Format wie anime_data.json, damit API und Datei dasselbe liefern.
STATE = {"payload": None, "scraping": False, "last_error": ""}
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
        with sync_playwright() as playwright:
            playwright.chromium.launch(headless=True).close()
    except Exception:
        print("📦 Installiere Playwright-Chromium...")
        os.system(f'"{sys.executable}" -m playwright install chromium')


def load_cache_into_state(settings: Settings) -> bool:
    """Gespeicherte Daten laden, damit der Server sofort antworten kann."""
    data = load(settings.data_file)
    if not any(data.get(name) for name in CATEGORY_ORDER):
        return False
    with STATE_LOCK:
        STATE["payload"] = data
    total = sum(len(data.get(name) or []) for name in CATEGORY_ORDER)
    print(f"💾 {total} Anime aus {os.path.basename(settings.data_file)} geladen "
          f"(Stand: {data.get('timestamp')})")
    return True


def run_pipeline(settings: Settings) -> None:
    """Einmal komplett durchlaufen – Quellen, Aufbewahrung, Speichern."""
    from . import pipeline

    with STATE_LOCK:
        if STATE["scraping"]:
            print("⚠️  Läuft bereits – übersprungen")
            return
        STATE["scraping"] = True
        STATE["last_error"] = ""

    try:
        report = pipeline.run(settings, path=settings.data_file, scrape=True)
        with STATE_LOCK:
            STATE["payload"] = report.payload
        pipeline.print_report(report, settings.data_file)
    except Exception as exc:                        # noqa: BLE001
        print(f"❌ Fehler beim Aktualisieren: {exc}")
        with STATE_LOCK:
            STATE["last_error"] = str(exc)
    finally:
        with STATE_LOCK:
            STATE["scraping"] = False


def auto_refresh_loop(settings: Settings, interval_hours: int = AUTO_REFRESH_HOURS) -> None:
    while True:
        time.sleep(interval_hours * 3600)
        print(f"\n🔄 Auto-Refresh (alle {interval_hours}h)...")
        run_pipeline(settings)


def create_app(settings: Settings):
    """Flask-App bauen (erst hier importieren, damit Tests ohne Flask laufen)."""
    from flask import Flask, jsonify, send_from_directory

    app = Flask(__name__)

    @app.route("/")
    def serve_index():
        if os.path.exists(HTML_FILE):
            with open(HTML_FILE, "r", encoding="utf-8") as handle:
                return handle.read()
        return "index.html nicht gefunden!", 404

    @app.route("/api/anime-data")
    def api_anime_data():
        """Aktueller Stand – identisches Format wie anime_data.json."""
        with STATE_LOCK:
            payload, scraping = STATE["payload"], STATE["scraping"]
        if payload:
            response = dict(payload)
            response["scraping"] = scraping
            response["source"] = "live"
            return jsonify(response)
        return jsonify({"error": "Noch keine Daten – Abruf läuft...", "scraping": scraping}), 503

    @app.route("/api/refresh")
    def api_refresh():
        with STATE_LOCK:
            if STATE["scraping"]:
                return jsonify({"status": "Läuft bereits...", "scraping": True})
        threading.Thread(target=run_pipeline, args=(settings,), daemon=True).start()
        return jsonify({"status": "Aktualisierung gestartet...", "scraping": True})

    @app.route("/api/status")
    def api_status():
        with STATE_LOCK:
            payload = STATE["payload"] or {}
            scraping, last_error = STATE["scraping"], STATE["last_error"]
        return jsonify({
            "status": "online",
            "counts": payload.get("counts", {name: 0 for name in CATEGORY_ORDER}),
            "total": payload.get("total", 0),
            "timestamp": payload.get("timestamp"),
            "updated_at": payload.get("updated_at"),
            "sources": payload.get("sources", []),
            "retention": payload.get("retention", {}),
            "warnings": payload.get("warnings", []),
            "scraping": scraping,
            "error": last_error,
            "version": payload.get("version"),
        })

    @app.route("/anime_data.json")
    def serve_json():
        if os.path.exists(settings.data_file):
            return send_from_directory(BASE_DIR, os.path.basename(settings.data_file))
        return jsonify({"error": "Keine Datei"}), 404

    @app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    return app


def main(auto_scrape: bool = True, port: int = 5000, settings: Settings | None = None) -> None:
    settings = settings or Settings.from_env()
    load_cache_into_state(settings)

    if auto_scrape:
        print("\n📥 Starte Aktualisierung im Hintergrund...")
        threading.Thread(target=run_pipeline, args=(settings,), daemon=True).start()
        threading.Thread(target=auto_refresh_loop, args=(settings,), daemon=True).start()

    print("\n" + "=" * 64)
    print(f"🚀 Server:  http://localhost:{port}")
    print(f"📡 API:     http://localhost:{port}/api/anime-data")
    print(f"🔄 Refresh: http://localhost:{port}/api/refresh")
    print(f"📊 Status:  http://localhost:{port}/api/status")
    print("🛑 Beenden: CTRL+C")
    print("=" * 64 + "\n")

    app = create_app(settings)
    try:
        app.run(debug=False, host="localhost", port=port, use_reloader=False)
    except KeyboardInterrupt:
        print("\n✅ Server beendet.")
