#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lokaler Server mit Menü (der klassische Doppelklick-Start).

    python scrape_anisearch_fixed.py
    Windows: Doppelklick auf "SERVER STARTEN.bat"

Ohne Menü geht es auch:  python -m tracker serve
"""

import sys

from tracker.config import Settings
from tracker.server import ensure_dependencies, main as serve, run_pipeline


def main() -> int:
    print("=" * 64)
    print("🎬 ANIME GER DUB TRACKER – SERVER")
    print("=" * 64)
    print("\nAbhängigkeiten werden geprüft...")
    ensure_dependencies()

    print("\n1. [Daten + Server]  Quellen abfragen & Server starten")
    print("2. [Nur Server]      Server mit gespeicherten Daten starten")
    print("3. [Nur Daten]       Quellen abfragen, kein Server\n")

    choice = (input("Auswahl (1/2/3) [Standard: 1]: ").strip() or "1")
    settings = Settings.from_env()

    if choice == "3":
        run_pipeline(settings)
        return 0

    serve(auto_scrape=choice != "2", settings=settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
