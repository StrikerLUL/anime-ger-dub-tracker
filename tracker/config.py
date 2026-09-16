#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zentrale Konfiguration des Trackers.

Alle Werte lassen sich per Umgebungsvariable überschreiben – so kann der
Workflow (oder ein lokaler Lauf) das Verhalten ändern, ohne dass Code
angefasst werden muss.

    TRACKER_MAX_AGE_DAYS=180 python -m tracker scrape
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

# ─── Pfade ────────────────────────────────────────────────────────────────────
# Immer relativ zum Projektverzeichnis, damit Doppelklick, cron und GitHub
# Actions dieselbe Datei schreiben statt versehentlich eine zweite anzulegen.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "anime_data.json")
HTML_FILE = os.path.join(BASE_DIR, "index.html")

#: Schema-Version von anime_data.json. Bei inhaltlichen Änderungen erhöhen.
DATA_VERSION = "6.0"

#: Reihenfolge = Priorität beim Entdoppeln. Ein Anime, der bereits in einer
#: weiter oben stehenden Kategorie steckt, wird aus den folgenden entfernt.
CATEGORY_ORDER = ("kommende", "aktuelle", "abgeschlossen")

CATEGORY_LABELS = {
    "kommende": "Bald verfügbar (geplante Syncros)",
    "aktuelle": "Kürzlich erschienen (laufende Syncros)",
    "abgeschlossen": "Abgeschlossene deutsche Syncros",
}

USER_AGENT = (
    "anime-ger-dub-tracker/6.0 (+https://github.com/StrikerLUL/anime-ger-dub-tracker)"
)
#: Für anisearch.de: ein echter Browser-UA, sonst greift der Bot-Schutz.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

#: Deutsche Anime-News-Feeds (RSS/Atom). Feeds, die nicht antworten, werden
#: übersprungen – der Lauf schlägt deswegen nicht fehl.
DEFAULT_NEWS_FEEDS = (
    "https://www.anime2you.de/feed/",
    "https://www.crunchyroll.com/de/news/rss",
    "https://anime2you.de/news/feed/",
)

#: Nur News mit diesen Stichworten landen in der Datei – der Tracker ist ein
#: Synchro-Tracker, kein allgemeiner News-Reader.
NEWS_KEYWORDS = (
    "synchro", "syncro", "dub", "deutsch", "german", "sprecher",
    "sprecherin", "vertonung", "ger-dub", "ger dub", "untertitel",
)


# ─── Hilfsfunktionen für Umgebungsvariablen ───────────────────────────────────

def env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(minimum, int(raw.strip()))
    except ValueError:
        return default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on", "ja")


def env_list(name: str, default: tuple) -> tuple:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return tuple(default)
    return tuple(part.strip() for part in raw.split(",") if part.strip())


# ─── Aufbewahrung (Retention) ─────────────────────────────────────────────────

@dataclass(frozen=True)
class Retention:
    """
    Wie lange Daten in anime_data.json bleiben dürfen.

    Damit liegt nichts mehr für immer in der Datei: Einträge, die es bei den
    Quellen nicht mehr gibt, verschwinden nach einer Karenzzeit, und jeder
    Eintrag hat ein hartes Verfallsdatum.
    """

    #: Harte Obergrenze je Eintrag, gerechnet ab dem ersten Auftauchen.
    max_age_days: int = 365
    #: Karenz für Einträge, die eine Quelle nicht mehr liefert.
    stale_grace_days: int = 14
    #: Wie lange ein abgelaufener Eintrag nicht erneut aufgenommen wird
    #: (sonst käme er am nächsten Tag sofort zurück).
    tombstone_days: int = 90
    #: Obergrenze an Einträgen je Kategorie (hält die Datei klein).
    max_entries_per_category: int = 400
    #: Obergrenze an gemerkten Verfallsdaten.
    max_tombstones: int = 600
    #: News sind Tagesgeschäft und verschwinden entsprechend schnell.
    news_max_age_days: int = 30
    news_max_items: int = 40

    @classmethod
    def from_env(cls) -> "Retention":
        base = cls()
        return replace(
            base,
            max_age_days=env_int("TRACKER_MAX_AGE_DAYS", base.max_age_days, minimum=1),
            stale_grace_days=env_int("TRACKER_STALE_GRACE_DAYS", base.stale_grace_days),
            tombstone_days=env_int("TRACKER_TOMBSTONE_DAYS", base.tombstone_days),
            max_entries_per_category=env_int(
                "TRACKER_MAX_ENTRIES", base.max_entries_per_category, minimum=1
            ),
            max_tombstones=env_int("TRACKER_MAX_TOMBSTONES", base.max_tombstones),
            news_max_age_days=env_int("TRACKER_NEWS_MAX_AGE_DAYS", base.news_max_age_days, minimum=1),
            news_max_items=env_int("TRACKER_NEWS_MAX_ITEMS", base.news_max_items),
        )

    def as_dict(self) -> dict:
        """Kompakte Fassung für anime_data.json (die Website kann sie anzeigen)."""
        return {
            "max_age_days": self.max_age_days,
            "stale_grace_days": self.stale_grace_days,
            "max_entries_per_category": self.max_entries_per_category,
            "news_max_age_days": self.news_max_age_days,
        }


# ─── Quellen ──────────────────────────────────────────────────────────────────

#: Reihenfolge = Ausführungsreihenfolge. anisearch liefert die Kategorien,
#: alles andere reichert an bzw. ergänzt.
ALL_SOURCES = ("anisearch", "anilist", "jikan", "news")


@dataclass(frozen=True)
class Settings:
    data_file: str = DATA_FILE
    retention: Retention = Retention()
    sources: tuple = ALL_SOURCES
    #: Wie viele Listenseiten je Kategorie von anisearch.de gelesen werden.
    max_pages: int = 5
    max_pages_done: int = 4
    #: Wartezeit zwischen Seitenaufrufen (Höflichkeit gegenüber anisearch.de).
    page_delay_ms: int = 1500
    #: Wie viele Titel je Lauf angereichert werden dürfen.
    anilist_budget: int = 240
    jikan_budget: int = 30
    #: Netzwerk-Timeout für die JSON-/RSS-Quellen.
    request_timeout: int = 20
    news_feeds: tuple = DEFAULT_NEWS_FEEDS

    @classmethod
    def from_env(cls) -> "Settings":
        base = cls(retention=Retention.from_env())
        sources = tuple(
            name for name in env_list("TRACKER_SOURCES", ALL_SOURCES)
            if name in ALL_SOURCES
        ) or ("anisearch",)
        # Einzelne Quellen gezielt abschalten: TRACKER_DISABLE_ANILIST=1
        sources = tuple(
            name for name in sources
            if not env_bool(f"TRACKER_DISABLE_{name.upper()}", False)
        )
        return replace(
            base,
            data_file=os.environ.get("TRACKER_DATA_FILE") or base.data_file,
            sources=sources,
            max_pages=env_int("TRACKER_MAX_PAGES", base.max_pages, minimum=1),
            max_pages_done=env_int("TRACKER_MAX_PAGES_DONE", base.max_pages_done, minimum=1),
            page_delay_ms=env_int("TRACKER_PAGE_DELAY_MS", base.page_delay_ms),
            anilist_budget=env_int("TRACKER_ANILIST_BUDGET", base.anilist_budget),
            jikan_budget=env_int("TRACKER_JIKAN_BUDGET", base.jikan_budget),
            request_timeout=env_int("TRACKER_REQUEST_TIMEOUT", base.request_timeout, minimum=1),
            news_feeds=env_list("TRACKER_NEWS_FEEDS", base.news_feeds),
        )

    def enabled(self, source: str) -> bool:
        return source in self.sources
