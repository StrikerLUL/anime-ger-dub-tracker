#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prüft anime_data.json, bevor sie committet bzw. auf den Webspace geladen wird.

Harte Fehler (Exit-Code 1) – die Datei darf so nicht veröffentlicht werden:
  * Datei fehlt oder ist kein gültiges JSON
  * gar keine Anime enthalten
  * ein Anime steht in mehr als einer Kategorie (Duplikat)
  * ein Anime steht doppelt innerhalb derselben Kategorie

Weiche Hinweise (Exit-Code 0, aber als GitHub-Actions-Warnung sichtbar):
  * Warnungen des Scrapers, z. B. ein von anisearch.de ignorierter Filter

Nutzbar auch lokal:  python check_data.py [pfad/zur/anime_data.json]
"""

import json
import os
import sys

from anisearch_scraper import CATEGORY_ORDER, DATA_FILE, anime_key


def gh_annotate(level: str, message: str) -> None:
    """Meldung zusätzlich als GitHub-Actions-Annotation ausgeben."""
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{level}::{message}")


def check(path: str = DATA_FILE) -> int:
    if not os.path.exists(path):
        print(f"❌ {path} fehlt – der Scraper hat nicht funktioniert")
        return 1

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        print(f"❌ {path} ist kein gültiges JSON: {e}")
        return 1

    errors: list = []
    owner: dict = {}      # Schlüssel -> (Kategorie, Titel)
    counts: dict = {}

    for name in CATEGORY_ORDER:
        entries = data.get(name) or []
        counts[name] = len(entries)
        local: dict = {}

        for anime in entries:
            key = anime_key(anime)
            title = anime.get("title", "?")

            if key in local:
                errors.append(f"'{title}' steht doppelt in '{name}'")
            local[key] = title

            if key in owner and owner[key][0] != name:
                errors.append(
                    f"'{title}' steht sowohl in '{owner[key][0]}' als auch in '{name}'"
                )
            else:
                owner.setdefault(key, (name, title))

    total = sum(counts.values())
    print(f"📊 {counts.get('kommende', 0)} kommende + "
          f"{counts.get('aktuelle', 0)} aktuelle + "
          f"{counts.get('abgeschlossen', 0)} abgeschlossene Dubs "
          f"= {total} Anime")
    print(f"🕒 Datenstand: {data.get('timestamp', 'unbekannt')}")
    print(f"🔑 Hash: {data.get('data_hash', 'n/a')}")

    if total == 0:
        print("❌ Keine Daten enthalten")
        return 1

    if errors:
        print(f"\n❌ {len(errors)} Duplikat(e) gefunden – Daten werden nicht veröffentlicht:")
        for e in errors[:20]:
            print(f"   • {e}")
        if len(errors) > 20:
            print(f"   • ... und {len(errors) - 20} weitere")
        gh_annotate("error", f"{len(errors)} doppelte Anime in anime_data.json")
        return 1

    print(f"✅ Keine Duplikate – jeder der {total} Anime steht genau einmal in der Datei")

    for warning in data.get("warnings", []):
        print(f"⚠️  {warning}")
        gh_annotate("warning", warning)

    return 0


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else DATA_FILE))
