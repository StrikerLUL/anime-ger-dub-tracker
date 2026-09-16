#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lesen und Schreiben von anime_data.json.

Zwei Zusagen:

* **Nichts wird ohne Grund neu geschrieben.** Sind die Daten gleich, bleibt die
  Datei Byte für Byte unverändert – kein Diff, kein Commit, keine endlos
  wachsende Historie.
* **Halb geschriebene Dateien gibt es nicht.** Geschrieben wird in eine
  temporäre Datei, die anschließend atomar an ihren Platz verschoben wird.

Das Format bleibt abwärtskompatibel: `kommende`, `aktuelle`, `abgeschlossen`,
`timestamp`, `source` und `version` gibt es weiterhin mit derselben Bedeutung –
bestehende Einbindungen (u. a. meine-anime-welt.de) laufen unverändert weiter.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

from .config import CATEGORY_ORDER, DATA_FILE, DATA_VERSION, Retention
from .models import content_of, count_entries, iso, utcnow

#: Felder, die sich bei jedem Lauf ändern dürfen, ohne dass das eine
#: inhaltliche Änderung wäre. Sie bleiben beim Vergleich außen vor.
VOLATILE_FIELDS = ("updated_at",)


def data_hash(categories: dict) -> str:
    """Content-Hash über die reinen Anime-Daten (ohne Zeitstempel/Buchhaltung)."""
    payload = {
        name: [content_of(anime) for anime in (categories.get(name) or [])]
        for name in CATEGORY_ORDER
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load(path: str = DATA_FILE) -> dict:
    """Vorhandene anime_data.json laden (leeres dict, wenn nicht lesbar)."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def build_payload(
    categories: dict,
    *,
    news=None,
    warnings=None,
    retired=None,
    previous=None,
    sources=None,
    retention: Retention | None = None,
    now: datetime | None = None,
) -> dict:
    """
    Die fertige JSON-Struktur bauen.

    `timestamp` und `data_changed_at` zeigen auf die letzte **inhaltliche**
    Änderung der Anime-Daten – nicht auf den letzten Lauf. Läuft der Scraper
    täglich ohne neue Daten, bleibt der Zeitstempel stehen (und damit die Datei
    unverändert).
    """
    now = now or utcnow()
    previous = previous or {}
    digest = data_hash(categories)

    changed_at = iso(now)
    if previous.get("data_hash") == digest:
        changed_at = (
            previous.get("data_changed_at")
            or previous.get("timestamp")
            or iso(now)
        )

    counts = count_entries(categories)
    payload = {name: categories.get(name) or [] for name in CATEGORY_ORDER}
    payload.update({
        "news": list(news or []),
        "timestamp": changed_at,          # abwärtskompatibel: letzter Datenstand
        "data_changed_at": changed_at,
        "data_hash": digest,
        "counts": {**counts, "news": len(news or [])},
        "total": sum(counts.values()),
        "source": "anisearch.de",         # abwärtskompatibel: Hauptquelle
        "sources": sorted(sources or ["anisearch.de"]),
        "version": DATA_VERSION,
        "retention": (retention or Retention()).as_dict(),
        "scraping": False,
        "warnings": list(warnings or []),
    })
    if retired:
        # Rückkehrsperre der Aufbewahrung. Für die Website ohne Bedeutung, sie
        # ignoriert unbekannte Felder – der Tracker braucht sie beim nächsten Lauf.
        payload["retired"] = dict(sorted(retired.items()))
    return payload


def comparable(payload: dict) -> dict:
    """Payload ohne die Felder, die sich sowieso bei jedem Schreibvorgang ändern."""
    return {key: value for key, value in (payload or {}).items() if key not in VOLATILE_FIELDS}


def write_if_changed(payload: dict, path: str = DATA_FILE, *, now: datetime | None = None) -> bool:
    """
    JSON nur schreiben, wenn sich wirklich etwas geändert hat.

    Verglichen wird der komplette Inhalt (Anime, News, Warnungen, Aufbewahrung)
    – nicht nur der Anime-Hash. So führt auch eine gelöschte Karteileiche zu
    einem Schreibvorgang, ein reiner Zeitstempel-Wechsel dagegen nicht.
    """
    previous = load(path)
    if comparable(previous) == comparable(payload):
        return False

    payload["updated_at"] = iso(now or utcnow())

    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp_path, path)   # atomar: nie eine halb geschriebene Datei ausliefern
    return True
