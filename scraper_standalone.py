#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anisearch.de Standalone-Scraper für GitHub Actions.

Kein Flask, kein Server – aktualisiert ausschließlich anime_data.json.
Die eigentliche Logik liegt in anisearch_scraper.py, damit es sie nur einmal
im Projekt gibt.

Exit-Codes:
  0  Erfolg (Daten aktualisiert oder unverändert)
  1  Scraping fehlgeschlagen – keine Daten gefunden
"""

import sys

from anisearch_scraper import DATA_FILE, print_summary, scrape_and_store


def main() -> int:
    print("=" * 60)
    print("🎬 ANISEARCH STANDALONE SCRAPER (GitHub Actions)")
    print("=" * 60)

    written, payload, _warnings = scrape_and_store(DATA_FILE)
    print_summary(payload, written, DATA_FILE)

    if payload.get("total", 0) == 0:
        print("\n❌ FEHLER: Keine Daten gefunden – Scraper hat nichts geladen!")
        return 1

    print("\n✅ Fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
