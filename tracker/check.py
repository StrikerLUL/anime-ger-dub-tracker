#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prüft anime_data.json, bevor sie committet bzw. auf den Webspace geladen wird.

Das ist die letzte Station vor der Website – was hier durchfällt, wird nicht
veröffentlicht.

Harte Fehler (Exit-Code 1):
  * Datei fehlt, ist kein gültiges JSON oder enthält gar keine Anime
  * ein Anime steht in mehr als einer Kategorie oder doppelt in derselben
  * Pflichtfelder fehlen (Titel, Link)
  * counts/total passen nicht zu den Listen, oder data_hash stimmt nicht
  * ein Eintrag hätte nach den Aufbewahrungsregeln längst gelöscht sein müssen

Weiche Hinweise (Exit-Code 0, in GitHub Actions als Warnung sichtbar):
  * Warnungen des Scrapers, z. B. ein von anisearch.de ignorierter Filter
  * Einträge ohne Bild, News ohne Datum

    python -m tracker check [pfad/zur/anime_data.json]
"""

from __future__ import annotations

import json
import os
import sys

from .config import CATEGORY_ORDER, Retention
from .models import anime_key, days_between, parse_iso, utcnow
from .store import data_hash


def gh_annotate(level: str, message: str) -> None:
    """Meldung zusätzlich als GitHub-Actions-Annotation ausgeben."""
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{level}::{message}")


def collect_problems(data: dict, *, now=None, policy: Retention | None = None) -> tuple:
    """Rückgabe: (fehler, hinweise) – reine Prüflogik, ohne Ausgabe."""
    now = now or utcnow()
    policy = policy or Retention.from_env()
    errors: list = []
    hints: list = []

    owner: dict = {}
    counts: dict = {}
    without_image = 0

    for name in CATEGORY_ORDER:
        entries = data.get(name)
        if entries is None:
            errors.append(f"Kategorie '{name}' fehlt in der Datei")
            entries = []
        if not isinstance(entries, list):
            errors.append(f"Kategorie '{name}' ist keine Liste")
            entries = []

        counts[name] = len(entries)
        local: dict = {}

        for anime in entries:
            if not isinstance(anime, dict):
                errors.append(f"{name}: Eintrag ist kein Objekt")
                continue

            title = (anime.get("title") or "").strip()
            if not title:
                errors.append(f"{name}: Eintrag ohne Titel (id={anime.get('id')})")
                continue
            if not (anime.get("url") or "").strip():
                errors.append(f"'{title}' hat keinen Link")
            if not (anime.get("image") or "").strip():
                without_image += 1

            key = anime_key(anime)
            if key in local:
                errors.append(f"'{title}' steht doppelt in '{name}'")
            local[key] = title

            if key in owner and owner[key][0] != name:
                errors.append(
                    f"'{title}' steht sowohl in '{owner[key][0]}' als auch in '{name}'"
                )
            else:
                owner.setdefault(key, (name, title))

            errors.extend(_retention_problems(anime, title, now, policy))

    total = sum(counts.values())
    if total == 0:
        errors.append("Keine Anime enthalten – der Scraper hat nichts geladen")

    stored_counts = data.get("counts") or {}
    for name in CATEGORY_ORDER:
        if name in stored_counts and stored_counts[name] != counts[name]:
            errors.append(
                f"counts['{name}'] = {stored_counts[name]}, tatsächlich sind es {counts[name]}"
            )
    if "total" in data and data["total"] != total:
        errors.append(f"total = {data['total']}, tatsächlich sind es {total}")

    if data.get("data_hash"):
        recomputed = data_hash({name: data.get(name) or [] for name in CATEGORY_ORDER})
        if recomputed != data["data_hash"]:
            errors.append("data_hash passt nicht zu den Daten in der Datei")

    errors.extend(_news_problems(data.get("news"), now, policy, hints))

    if without_image:
        hints.append(f"{without_image} Anime ohne Coverbild")
    for warning in data.get("warnings") or []:
        hints.append(str(warning))

    return errors, hints


def _retention_problems(anime: dict, title: str, now, policy: Retention) -> list:
    """Hätte dieser Eintrag längst gelöscht sein müssen?"""
    problems = []

    expires_at = parse_iso(anime.get("expires_at"))
    if expires_at and expires_at <= now:
        problems.append(f"'{title}' ist seit {anime['expires_at']} abgelaufen und liegt noch in der Datei")

    missing_since = parse_iso(anime.get("missing_since"))
    if missing_since and days_between(now, missing_since) > policy.stale_grace_days + 1:
        problems.append(
            f"'{title}' wird seit {anime['missing_since']} von keiner Quelle mehr geliefert "
            f"und hätte gelöscht sein müssen"
        )

    first_seen = parse_iso(anime.get("first_seen"))
    if first_seen and days_between(now, first_seen) > policy.max_age_days + 1:
        problems.append(
            f"'{title}' ist älter als die erlaubten {policy.max_age_days} Tage"
        )
    return problems


def _news_problems(news, now, policy: Retention, hints: list) -> list:
    if news is None:
        return []
    if not isinstance(news, list):
        return ["'news' ist keine Liste"]

    errors = []
    if len(news) > policy.news_max_items:
        errors.append(f"{len(news)} News gespeichert, erlaubt sind {policy.news_max_items}")

    undated = 0
    for item in news:
        if not isinstance(item, dict) or not item.get("title") or not item.get("url"):
            errors.append("News-Eintrag ohne Titel oder Link")
            continue
        published = parse_iso(item.get("published"))
        if published is None:
            undated += 1
        elif days_between(now, published) > policy.news_max_age_days + 1:
            errors.append(f"News vom {item['published']} ist zu alt und liegt noch in der Datei")
    if undated:
        hints.append(f"{undated} News ohne Datum")
    return errors


def check(path: str, *, now=None) -> int:
    if not os.path.exists(path):
        print(f"❌ {path} fehlt – der Scraper hat nicht funktioniert")
        return 1

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except ValueError as exc:
        print(f"❌ {path} ist kein gültiges JSON: {exc}")
        return 1

    if not isinstance(data, dict):
        print(f"❌ {path} enthält kein Objekt")
        return 1

    errors, hints = collect_problems(data, now=now)
    counts = {name: len(data.get(name) or []) for name in CATEGORY_ORDER}
    total = sum(counts.values())

    print(f"📊 {counts['kommende']} kommende + {counts['aktuelle']} aktuelle + "
          f"{counts['abgeschlossen']} abgeschlossene Dubs = {total} Anime")
    print(f"📰 {len(data.get('news') or [])} News")
    print(f"🕒 Datenstand: {data.get('timestamp', 'unbekannt')}")
    print(f"🔑 Hash: {data.get('data_hash', 'n/a')}")
    print(f"🗃️  Aufbewahrung: {data.get('retention', {})}")
    print(f"📡 Quellen: {', '.join(data.get('sources') or [data.get('source', '?')])}")

    if errors:
        print(f"\n❌ {len(errors)} Problem(e) – die Daten werden nicht veröffentlicht:")
        for problem in errors[:25]:
            print(f"   • {problem}")
        if len(errors) > 25:
            print(f"   • ... und {len(errors) - 25} weitere")
        gh_annotate("error", f"{len(errors)} Problem(e) in anime_data.json")
        return 1

    print(f"✅ Alles in Ordnung – jeder der {total} Anime steht genau einmal in der Datei")
    for hint in hints:
        print(f"⚠️  {hint}")
        gh_annotate("warning", hint)
    return 0


if __name__ == "__main__":
    from .config import DATA_FILE
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else DATA_FILE))
