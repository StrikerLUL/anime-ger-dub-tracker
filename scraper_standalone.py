#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einstieg für GitHub Actions: Quellen abfragen und anime_data.json aktualisieren.

Kein Flask, kein Server. Die eigentliche Arbeit macht das Paket `tracker`.
Identisch zu:  python -m tracker scrape

Exit-Codes:
  0  Erfolg (Daten aktualisiert oder unverändert)
  1  Lauf fehlgeschlagen – keine Daten gefunden
"""

import sys

from tracker.cli import main

if __name__ == "__main__":
    sys.exit(main(["scrape", *sys.argv[1:]]))
