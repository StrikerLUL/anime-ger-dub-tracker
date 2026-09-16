#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kommandozeile des Trackers.

    python -m tracker scrape     # Quellen abfragen und anime_data.json aktualisieren
    python -m tracker prune      # nur aufräumen (ohne Scraping)
    python -m tracker check      # anime_data.json prüfen
    python -m tracker info       # aktuellen Stand und Einstellungen anzeigen
    python -m tracker serve      # lokalen Server starten

Exit-Codes:
  0  alles gut
  1  Lauf fehlgeschlagen (keine Daten, Quelle tot, Prüfung durchgefallen)
"""

from __future__ import annotations

import argparse
import sys

from .config import CATEGORY_ORDER, DATA_VERSION, Settings


def _banner(title: str) -> None:
    print("=" * 64)
    print(title)
    print("=" * 64)


def cmd_scrape(args) -> int:
    from . import pipeline

    settings = Settings.from_env()
    path = args.data or settings.data_file
    _banner(f"🎬 ANIME GER DUB TRACKER {DATA_VERSION} – Quellen: {', '.join(settings.sources)}")

    report = pipeline.run(settings, path=path, scrape=True)
    pipeline.print_report(report, path)

    if report.total == 0:
        print("\n❌ FEHLER: Keine Daten – der Lauf hat nichts geliefert!")
        return 1
    if not report.sources_ok:
        print("\n⚠️  Hauptquelle gestört – vorhandene Daten wurden unverändert behalten.")
        return 1 if args.strict else 0
    return 0


def cmd_prune(args) -> int:
    from . import pipeline

    settings = Settings.from_env()
    path = args.data or settings.data_file
    _banner("🧹 AUFRÄUMEN – alte und verschwundene Einträge entfernen")

    report = pipeline.run(settings, path=path, scrape=False)
    pipeline.print_report(report, path)
    return 0


def cmd_check(args) -> int:
    from .check import check

    settings = Settings.from_env()
    return check(args.data or settings.data_file)


def cmd_info(args) -> int:
    from .store import load

    settings = Settings.from_env()
    path = args.data or settings.data_file
    data = load(path)

    _banner("ℹ️  ANIME GER DUB TRACKER")
    print(f"Datei:        {path}")
    print(f"Schema:       {data.get('version', '–')} (Code: {DATA_VERSION})")
    print(f"Datenstand:   {data.get('timestamp', '–')}")
    print(f"Zuletzt neu:  {data.get('updated_at', '–')}")
    print(f"Quellen:      {', '.join(data.get('sources') or ['–'])}")
    print(f"Anime:        {data.get('total', 0)}")
    for name in CATEGORY_ORDER:
        print(f"   {name:<14} {len(data.get(name) or []):>4}")
    print(f"News:         {len(data.get('news') or [])}")
    print(f"Gesperrt:     {len(data.get('retired') or {})} (Rückkehrsperre)")
    print("\nEinstellungen (per Umgebungsvariable änderbar):")
    print(f"   Aufbewahrung:     {settings.retention.max_age_days} Tage")
    print(f"   Karenz:           {settings.retention.stale_grace_days} Tage")
    print(f"   Max. je Kategorie:{settings.retention.max_entries_per_category:>5}")
    print(f"   Aktive Quellen:   {', '.join(settings.sources)}")
    for warning in data.get("warnings") or []:
        print(f"⚠️  {warning}")
    return 0


def cmd_serve(args) -> int:
    from .server import main as serve_main

    serve_main(auto_scrape=args.scrape, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tracker",
        description="Anime Ger Dub Tracker – deutsche Synchronisationen verfolgen",
    )
    parser.add_argument("--data", help="Pfad zu anime_data.json")
    sub = parser.add_subparsers(dest="command")

    scrape = sub.add_parser("scrape", help="Quellen abfragen und Daten aktualisieren")
    scrape.add_argument("--strict", action="store_true",
                        help="Auch dann fehlschlagen, wenn nur die Hauptquelle gestört war")
    scrape.set_defaults(func=cmd_scrape)

    sub.add_parser("prune", help="Nur aufräumen, nicht scrapen").set_defaults(func=cmd_prune)
    sub.add_parser("check", help="anime_data.json prüfen").set_defaults(func=cmd_check)
    sub.add_parser("info", help="Aktuellen Stand anzeigen").set_defaults(func=cmd_info)

    serve = sub.add_parser("serve", help="Lokalen Server starten")
    serve.add_argument("--port", type=int, default=5000)
    serve.add_argument("--scrape", action="store_true", help="Beim Start einmal scrapen")
    serve.set_defaults(func=cmd_serve)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
