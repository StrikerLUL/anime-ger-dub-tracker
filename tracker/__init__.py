# -*- coding: utf-8 -*-
"""
Anime Ger Dub Tracker – Datenpipeline.

Verfolgt deutsche Anime-Synchronisationen und schreibt sie nach
anime_data.json. Aufbau:

    tracker/config.py      Einstellungen (per Umgebungsvariable änderbar)
    tracker/models.py      Datenmodell, Titelabgleich, Zeitrechnung
    tracker/sources/       anisearch.de, AniList, MyAnimeList, News-Feeds
    tracker/merge.py       Zusammenführen und Entdoppeln
    tracker/retention.py   Aufbewahrung – alte Daten verschwinden wieder
    tracker/store.py       Lesen/Schreiben von anime_data.json
    tracker/pipeline.py    der komplette Ablauf
    tracker/check.py       Qualitätsprüfung vor der Veröffentlichung
"""

from .config import CATEGORY_LABELS, CATEGORY_ORDER, DATA_FILE, DATA_VERSION, Settings

__version__ = "6.0.0"

__all__ = [
    "CATEGORY_LABELS",
    "CATEGORY_ORDER",
    "DATA_FILE",
    "DATA_VERSION",
    "Settings",
    "__version__",
]
