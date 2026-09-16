#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Datenmodell und reine Hilfsfunktionen.

Alles hier ist netzwerkfrei und deterministisch – damit ist es in Tests
vollständig abgedeckt und läuft in GitHub Actions vor jedem Scraping-Lauf.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone

from .config import CATEGORY_ORDER

ANIME_TYPES = ("TV-Serie", "Film", "OVA", "Web", "TV-Spezial", "Bonus", "Musikvideo")

#: Felder, die einen Anime inhaltlich beschreiben. Nur sie fließen in den
#: data_hash ein – Buchhaltung (first_seen, missing_since …) bleibt außen vor,
#: damit ein Lauf ohne echte Änderung auch keinen Datei-Diff erzeugt.
CONTENT_FIELDS = (
    "id", "title", "url", "image", "info", "year", "type",
    "episodes", "genres", "studios", "score", "season", "external",
)

#: Buchhaltungsfelder der Aufbewahrung.
BOOKKEEPING_FIELDS = ("first_seen", "expires_at", "missing_since", "sources")

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


# ─── Zeit ─────────────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(moment: datetime) -> str:
    """UTC-Zeitstempel im Format 2026-09-16T10:00:00Z."""
    return moment.astimezone(timezone.utc).strftime(ISO_FORMAT)


def parse_iso(value) -> datetime | None:
    """Zeitstempel einlesen – tolerant gegenüber älteren Schreibweisen."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def days_between(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds() / 86400.0


def plus_days(moment: datetime, days: int) -> datetime:
    return moment + timedelta(days=days)


# ─── Anime-Felder ─────────────────────────────────────────────────────────────

def extract_year(info: str) -> int:
    """Jahr aus einem Info-String wie 'TV-Serie, 12 (2024)' lesen."""
    m = re.search(r"\((\d{4})\)", info or "")
    if m:
        return int(m.group(1))
    m = re.search(r"\b((?:19|20)\d{2})\b", info or "")
    return int(m.group(1)) if m else 0


def extract_type(info: str) -> str:
    """Medienformat aus dem Info-String lesen."""
    for anime_type in ANIME_TYPES:
        if anime_type in (info or ""):
            return anime_type
    return "Anime"


def extract_episodes(info: str) -> int:
    """
    Episodenzahl aus 'TV-Serie, 12 (2024)' lesen.

    Filme ohne Angabe zählen als eine Episode, alles Unbekannte als 0.
    """
    m = re.search(r",\s*(\d{1,4})\b", info or "")
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,4})\s*(?:Episoden|Folgen|Eps?)\b", info or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def anime_key(anime: dict) -> str:
    """
    Stabiler Schlüssel für Deduplizierung und Aufbewahrung.

    Normalerweise die anisearch-ID. Fehlt sie (Parser-Ausfall, id == 0), wird
    auf URL bzw. Titel ausgewichen – sonst fielen alle Einträge ohne ID auf
    denselben Schlüssel zusammen und würden fälschlich verworfen.
    """
    anime_id = anime.get("id") or 0
    if anime_id:
        return f"id:{anime_id}"
    url = (anime.get("url") or "").strip().lower()
    if url:
        return f"url:{url}"
    return f"title:{normalize_title(anime.get('title') or '')}"


# ─── Titel-Normalisierung (für den Abgleich zwischen den Quellen) ─────────────

_ROMAN = {
    " ii": " 2", " iii": " 3", " iv": " 4", " v": " 5",
    " vi": " 6", " vii": " 7", " viii": " 8", " ix": " 9",
}
_NOISE = re.compile(r"\b(the|a|an|der|die|das|season|staffel|part|teil|cour)\b")


def normalize_title(title: str) -> str:
    """
    Titel auf eine vergleichbare Form bringen.

    anisearch.de, AniList und MyAnimeList schreiben denselben Anime gern
    unterschiedlich ('Re:Zero − Starting Life…' vs 'Re Zero kara Hajimeru…').
    Ohne Normalisierung findet der Abgleich nichts – mit zu lockerer
    Normalisierung findet er das Falsche. Deshalb: Akzente, Satzzeichen und
    Füllwörter raus, Rest bleibt.
    """
    text = unicodedata.normalize("NFKD", str(title or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", " and ").replace("+", " plus ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = f" {text.strip()} "
    for roman, arabic in _ROMAN.items():
        text = text.replace(f"{roman} ", f"{arabic} ")
    text = _NOISE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_candidates(anime: dict) -> list:
    """Alle Schreibweisen, unter denen ein Anime bei anderen Quellen stehen kann."""
    values = [anime.get("title")]
    values.extend(anime.get("titles") or [])
    seen, out = set(), []
    for value in values:
        norm = normalize_title(value)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


# ─── Sortierung ───────────────────────────────────────────────────────────────

def sort_animes(animes: list) -> list:
    """
    Deterministische Reihenfolge: neueste zuerst, dann alphabetisch.

    Die Anzeige-Sortierung übernimmt ohnehin das Frontend. Eine feste
    Reihenfolge in der Datei sorgt dafür, dass unveränderte Daten auch einen
    unveränderten Dateiinhalt ergeben – sonst erzeugt jede Umsortierung durch
    anisearch.de einen Diff und damit einen überflüssigen Commit.
    """
    return sorted(
        animes,
        key=lambda a: (-(a.get("year") or 0), (a.get("title") or "").lower(), anime_key(a)),
    )


def content_of(anime: dict) -> dict:
    """Nur die inhaltlichen Felder – Grundlage für den data_hash."""
    return {field: anime[field] for field in CONTENT_FIELDS if field in anime}


def count_entries(categories: dict) -> dict:
    return {name: len(categories.get(name) or []) for name in CATEGORY_ORDER}
