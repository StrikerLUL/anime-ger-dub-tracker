#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zusammenführen und Entdoppeln der Quelldaten.

Kernzusage: **Kein Anime steht doppelt in der Datei.** Liefert anisearch.de
denselben Eintrag in mehreren Filter-Abfragen, gewinnt die Kategorie mit der
höheren Priorität; in allen anderen wird er entfernt.

Dazu kommt eine Notlösung für den Fall, dass anisearch.de einen Filter
ignoriert: dann werden die Kategorien anhand des Erscheinungsjahres getrennt,
statt 200 Anime pauschal als "kürzlich erschienen" auszugeben.
"""

from __future__ import annotations

from .config import CATEGORY_ORDER
from .models import anime_key, normalize_title, sort_animes

#: Ab diesem Überlappungsgrad gelten zwei Filter-Abfragen als identisch.
FILTER_OVERLAP_LIMIT = 0.9

#: Wie viele Jahre ein Anime zurückliegen muss, damit seine Synchro bei
#: kaputtem Filter als "abgeschlossen" gilt. Bewusst großzügig – lieber ein
#: Anime zu viel in "aktuelle" als eine falsche Behauptung.
DONE_AFTER_YEARS = 2


def dedupe_categories(raw: dict) -> tuple:
    """
    Kategorien zusammenführen und entdoppeln.

    Rückgabe: (kategorien, warnungen)

    * Innerhalb einer Kategorie bleibt je Anime nur der erste Treffer.
    * Über Kategorien hinweg gewinnt die Kategorie mit der höheren Priorität.
    * Liefern zwei Filter-Abfragen (nahezu) dieselbe Menge, ist das ein Zeichen
      dafür, dass anisearch.de den Filter ignoriert hat. Das wird gemeldet,
      statt die Daten doppelt zu speichern.
    """
    categories: dict = {}
    warnings: list = []
    seen: dict = {}          # Schlüssel -> Kategorie, die den Anime bekommen hat
    raw_keys: dict = {}      # Kategorie -> Schlüsselmenge vor dem Entdoppeln

    for name in CATEGORY_ORDER:
        entries = raw.get(name) or []
        unique: list = []
        local_seen: set = set()
        dropped_internal = 0
        dropped_cross: dict = {}

        for anime in entries:
            if not (anime.get("title") or "").strip():
                continue
            key = anime_key(anime)

            if key in local_seen:
                dropped_internal += 1
                continue
            local_seen.add(key)

            owner = seen.get(key)
            if owner is not None:
                dropped_cross[owner] = dropped_cross.get(owner, 0) + 1
                continue

            seen[key] = name
            entry = dict(anime)
            entry["status"] = name
            unique.append(entry)

        raw_keys[name] = local_seen
        categories[name] = sort_animes(unique)

        if dropped_internal:
            warnings.append(
                f"{name}: {dropped_internal} Duplikat(e) innerhalb der Kategorie entfernt"
            )
        for owner, count in dropped_cross.items():
            warnings.append(
                f"{name}: {count} Eintrag/Einträge entfernt, die bereits in '{owner}' stehen"
            )

    warnings.extend(filter_warnings(raw_keys))
    return categories, warnings


def filter_warnings(raw_keys: dict) -> list:
    """Identische Ergebnismengen deuten auf einen ignorierten Filter hin."""
    warnings = []
    names = list(CATEGORY_ORDER)
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            a, b = raw_keys.get(first) or set(), raw_keys.get(second) or set()
            if not a or not b:
                continue
            overlap = len(a & b) / min(len(a), len(b))
            if overlap >= FILTER_OVERLAP_LIMIT:
                warnings.append(
                    f"Filter greift nicht: '{first}' und '{second}' liefern zu "
                    f"{overlap:.0%} dieselben Anime – bitte CATEGORY_PARAMS in "
                    f"tracker/sources/anisearch.py gegen anisearch.de prüfen"
                )
    return warnings


def filter_broken(warnings) -> bool:
    return any(str(w).startswith("Filter greift nicht") for w in warnings)


def split_by_year(categories: dict, current_year: int) -> tuple:
    """
    Notlösung bei kaputtem anisearch-Filter.

    Ohne sie landet alles in 'aktuelle' – auch Syncros von 2009 – und die
    Kategorie 'abgeschlossen' bleibt leer. Hier wandern Einträge, deren Anime
    mindestens `DONE_AFTER_YEARS` Jahre alt ist, nach 'abgeschlossen'. Das ist
    eine Schätzung und wird als solche gemeldet.
    """
    cutoff = current_year - DONE_AFTER_YEARS
    moved = 0
    result = {name: list(categories.get(name) or []) for name in CATEGORY_ORDER}

    keep = []
    for entry in result.get("aktuelle", []):
        year = entry.get("year") or 0
        if 0 < year <= cutoff:
            moved_entry = dict(entry)
            moved_entry["status"] = "abgeschlossen"
            moved_entry["status_geschaetzt"] = True
            result.setdefault("abgeschlossen", []).append(moved_entry)
            moved += 1
        else:
            keep.append(entry)
    result["aktuelle"] = keep

    warnings = []
    if moved:
        warnings.append(
            f"{moved} Anime bis Jahrgang {cutoff} wurden anhand des Erscheinungsjahres "
            f"als 'abgeschlossen' eingeordnet (Schätzung, weil der anisearch-Filter "
            f"nicht greift)"
        )
    for name in CATEGORY_ORDER:
        result[name] = sort_animes(result.get(name, []))
    return result, warnings


def attach_metadata(categories: dict, metadata: dict) -> int:
    """
    Fakten aus AniList/Jikan an die passenden Anime hängen.

    Zugeordnet wird über den normalisierten Titel; nur eindeutige Treffer
    zählen. Vorhandene anisearch-Werte bleiben stehen – anisearch.de ist für
    Titel, Link und Kategorie die Wahrheit.
    """
    enriched = 0
    for name in CATEGORY_ORDER:
        for entry in categories.get(name) or []:
            facts = metadata.get(normalize_title(entry.get("title") or ""))
            if not facts:
                continue

            changed = False
            for key in ("genres", "studios", "score", "season"):
                value = facts.get(key)
                if value and not entry.get(key):
                    entry[key] = value
                    changed = True

            if facts.get("episodes") and not entry.get("episodes"):
                entry["episodes"] = facts["episodes"]
                changed = True

            if facts.get("cover") and not entry.get("image"):
                entry["image"] = facts["cover"]
                changed = True

            external = dict(entry.get("external") or {})
            for key, value in (facts.get("external") or {}).items():
                if value and key not in external:
                    external[key] = value
                    changed = True
            if external:
                entry["external"] = external

            if changed:
                enriched += 1
    return enriched


def titles_needing_metadata(categories: dict) -> list:
    """
    Titel, für die noch keine Zusatzdaten vorliegen.

    So wird jeder Anime genau einmal nachgeschlagen – und nicht jeden Tag neu.
    """
    wanted = []
    seen = set()
    for name in CATEGORY_ORDER:
        for entry in categories.get(name) or []:
            if entry.get("genres") or (entry.get("external") or {}).get("anilist"):
                continue
            title = (entry.get("title") or "").strip()
            norm = normalize_title(title)
            if title and norm not in seen:
                seen.add(norm)
                wanted.append(title)
    return wanted
