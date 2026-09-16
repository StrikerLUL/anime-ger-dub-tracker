#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Der komplette Ablauf eines Laufs.

    anisearch.de  ──┐
    AniList       ──┤→ zusammenführen → entdoppeln → Aufbewahrung → anime_data.json
    MyAnimeList   ──┤
    News-Feeds    ──┘

Alles ist gegen Ausfälle abgesichert: Jede Quelle läuft in ihrer eigenen
Fehlerbehandlung, und wenn anisearch.de nichts (oder auffällig wenig) liefert,
bleibt der Bestand unangetastet, statt die Website leerzuräumen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import merge, retention, store
from .config import CATEGORY_ORDER, Settings
from .models import utcnow
from .sources import anilist, anisearch, jikan, news as news_source
from .sources.base import SourceReport, run_source

#: Fällt die frische Datenmenge unter diesen Anteil des Bestands, gehen wir von
#: einer Störung aus und markieren nichts als verschwunden.
SANITY_RATIO = 0.5


@dataclass
class RunReport:
    """Ergebnis eines Laufs – alles, was das CLI und die CI wissen müssen."""

    written: bool = False
    payload: dict = field(default_factory=dict)
    reports: list = field(default_factory=list)
    stats: retention.RetentionStats = field(default_factory=retention.RetentionStats)
    enriched: int = 0
    sources_ok: bool = True

    @property
    def total(self) -> int:
        return int(self.payload.get("total", 0))

    @property
    def failed_sources(self) -> list:
        return [r.name for r in self.reports if not r.ok]


def _previous_categories(previous: dict) -> dict:
    return {name: list(previous.get(name) or []) for name in CATEGORY_ORDER}


def collect_metadata(categories: dict, settings: Settings, reports: list) -> dict:
    """AniList zuerst, MyAnimeList nur für den Rest – das spart Anfragen."""
    metadata: dict = {}
    wanted = merge.titles_needing_metadata(categories)
    if not wanted:
        return metadata

    if settings.enabled("anilist"):
        found, report = run_source(
            "anilist", anilist.lookup, wanted,
            timeout=settings.request_timeout, budget=settings.anilist_budget,
        )
        reports.append(report)
        metadata.update(found or {})

    if settings.enabled("jikan"):
        rest = [t for t in wanted if merge.normalize_title(t) not in metadata]
        if rest:
            found, report = run_source(
                "jikan", jikan.lookup, rest,
                timeout=settings.request_timeout, budget=settings.jikan_budget,
            )
            reports.append(report)
            metadata.update(found or {})

    return metadata


def run(
    settings: Settings | None = None,
    *,
    path: str | None = None,
    now: datetime | None = None,
    scrape: bool = True,
) -> RunReport:
    """
    Einen kompletten Lauf ausführen.

    `scrape=False` führt nur Aufbewahrung und News aus – das nutzt der
    Housekeeping-Workflow, damit alte Daten auch dann verschwinden, wenn der
    Scraper gerade klemmt.
    """
    settings = settings or Settings.from_env()
    path = path or settings.data_file
    now = now or utcnow()

    previous = store.load(path)
    previous_total = sum(len(previous.get(name) or []) for name in CATEGORY_ORDER)
    reports: list = []
    warnings: list = []
    sources_ok = True

    # ── 1. anisearch.de: die Kategorien ───────────────────────────────────────
    if scrape and settings.enabled("anisearch"):
        raw, report = run_source("anisearch", anisearch.scrape, settings)
        reports.append(report)
        if not report.ok or not raw:
            sources_ok = False
            warnings.append("anisearch.de war nicht erreichbar – Bestand bleibt unverändert")
            raw = _previous_categories(previous)
    else:
        # Housekeeping-Lauf ohne Scraping: der Bestand bleibt, wie er ist.
        # `raw` bleibt leer, damit die Aufbewahrung die vorhandenen
        # `missing_since`-Markierungen nicht versehentlich zurücksetzt –
        # Höchstalter und Obergrenzen greifen trotzdem.
        raw = {}
        reports.append(SourceReport(name="bestand", ok=True, items=previous_total))
        warnings.extend(previous.get("warnings") or [])
        sources_ok = False

    fresh_total = sum(len(raw.get(name) or []) for name in CATEGORY_ORDER)
    if sources_ok and previous_total and fresh_total < previous_total * SANITY_RATIO:
        sources_ok = False
        warnings.append(
            f"Nur {fresh_total} statt zuletzt {previous_total} Anime geladen – "
            f"verdächtig wenig, deshalb wird diesmal nichts als verschwunden markiert"
        )

    # ── 2. Entdoppeln ─────────────────────────────────────────────────────────
    categories, dedupe_warnings = merge.dedupe_categories(raw)
    warnings.extend(dedupe_warnings)

    # ── 3. Notlösung, falls anisearch.de den Filter ignoriert ─────────────────
    if merge.filter_broken(dedupe_warnings):
        categories, split_warnings = merge.split_by_year(categories, now.year)
        warnings.extend(split_warnings)

    # ── 4. Aufbewahrung: alte und verschwundene Daten entfernen ───────────────
    categories, retired, stats = retention.apply(
        categories, previous, now=now, policy=settings.retention, sources_ok=sources_ok,
    )

    # ── 5. Zusatzdaten von AniList / MyAnimeList ──────────────────────────────
    enriched = 0
    metadata = collect_metadata(categories, settings, reports)
    if metadata:
        enriched = merge.attach_metadata(categories, metadata)

    # ── 6. News ───────────────────────────────────────────────────────────────
    items = list(previous.get("news") or [])
    if settings.enabled("news"):
        fetched, report = run_source(
            "news", news_source.fetch, settings.news_feeds,
            timeout=settings.request_timeout,
            max_items=settings.retention.news_max_items,
            max_age_days=settings.retention.news_max_age_days,
        )
        reports.append(report)
        if report.ok and fetched:
            seen = {item.get("url") for item in fetched}
            items = list(fetched) + [i for i in items if i.get("url") not in seen]
    items = retention.prune_news(items, now=now, policy=settings.retention)

    # ── 7. Speichern (nur bei echter Änderung) ────────────────────────────────
    payload = store.build_payload(
        categories,
        news=items,
        warnings=warnings,
        retired=retired,
        previous=previous,
        # Provenienz: die aktiven Quellen des Trackers. Bewusst die
        # Konfiguration und nicht das Tagesergebnis – sonst änderte sich die
        # Datei schon, weil ein Feed einmal nicht antwortet.
        sources=list(settings.sources),
        retention=settings.retention,
        now=now,
    )
    written = store.write_if_changed(payload, path, now=now)

    return RunReport(
        written=written, payload=payload, reports=reports,
        stats=stats, enriched=enriched, sources_ok=sources_ok,
    )


def print_report(report: RunReport, path: str) -> None:
    payload = report.payload
    counts = payload.get("counts", {})

    print(f"\n{'=' * 64}")
    print("📡 Quellen")
    for source_report in report.reports:
        print(f"   {source_report.line()}")

    print("\n🗃️  Aufbewahrung")
    for line in report.stats.lines():
        print(f"   {line}")
    if report.enriched:
        print(f"   ✨ {report.enriched} Anime mit Zusatzdaten angereichert")

    print(f"\n📊 GESAMT: {payload.get('total', 0)} Anime (jeder genau einmal)")
    print(f"   {counts.get('kommende', 0)} geplant | "
          f"{counts.get('aktuelle', 0)} aktuell | "
          f"{counts.get('abgeschlossen', 0)} abgeschlossen | "
          f"{counts.get('news', 0)} News")
    print("=" * 64)

    for warning in payload.get("warnings", []):
        print(f"⚠️  {warning}")

    if report.written:
        print(f"\n💾 {path} aktualisiert (Stand: {payload.get('data_changed_at')})")
    else:
        print(f"\n✅ Keine Änderung – {path} bleibt unverändert (kein Commit nötig)")
