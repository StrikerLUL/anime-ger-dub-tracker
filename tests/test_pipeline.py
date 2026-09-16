# -*- coding: utf-8 -*-
"""
Tests des Gesamtablaufs – mit erfundenen Quellen, ohne Netzwerk.

Hier hängt alles zusammen: scrapen → entdoppeln → aufbewahren → speichern.
"""

from dataclasses import replace
from datetime import timedelta

from tests.conftest import anime
from tracker import pipeline
from tracker.models import iso
from tracker.store import load


def fake_scrape(result):
    def _scrape(settings, categories=None):
        return result
    return _scrape


def patch_sources(monkeypatch, *, scrape_result=None, metadata=None, news_items=None, fail=False):
    if fail:
        def boom(settings, categories=None):
            raise RuntimeError("anisearch.de nicht erreichbar")
        monkeypatch.setattr(pipeline.anisearch, "scrape", boom)
    else:
        monkeypatch.setattr(pipeline.anisearch, "scrape", fake_scrape(scrape_result or {}))

    monkeypatch.setattr(pipeline.anilist, "lookup", lambda titles, **kw: dict(metadata or {}))
    monkeypatch.setattr(pipeline.jikan, "lookup", lambda titles, **kw: {})
    monkeypatch.setattr(pipeline.news_source, "fetch", lambda feeds, **kw: list(news_items or []))


def test_kompletter_lauf_schreibt_die_datei(monkeypatch, settings, now):
    patch_sources(monkeypatch, scrape_result={
        "kommende": [anime(1, "Eins")],
        "aktuelle": [anime(2, "Zwei")],
        "abgeschlossen": [],
    })

    report = pipeline.run(settings, now=now)

    assert report.written is True
    assert report.total == 2
    data = load(settings.data_file)
    assert data["counts"]["kommende"] == 1
    assert data["timestamp"] == iso(now)
    assert data["version"]


def test_zweiter_lauf_ohne_aenderung_schreibt_nichts(monkeypatch, settings, now):
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1)]})
    pipeline.run(settings, now=now)
    before = open(settings.data_file, "rb").read()

    report = pipeline.run(settings, now=now + timedelta(days=1))

    assert report.written is False
    assert open(settings.data_file, "rb").read() == before


def test_verschwundener_anime_verschwindet_nach_der_karenz(monkeypatch, settings, now):
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1), anime(2)]})
    pipeline.run(settings, now=now)

    # Anime 2 taucht nicht mehr auf
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1)]})
    pipeline.run(settings, now=now + timedelta(days=1))
    assert len(load(settings.data_file)["aktuelle"]) == 2, "Karenzzeit greift noch"

    later = now + timedelta(days=settings.retention.stale_grace_days + 2)
    pipeline.run(settings, now=later)

    entries = load(settings.data_file)["aktuelle"]
    assert [e["id"] for e in entries] == [1]


def test_gestoerte_hauptquelle_behaelt_die_daten(monkeypatch, settings, now):
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1), anime(2)]})
    pipeline.run(settings, now=now)

    patch_sources(monkeypatch, fail=True)
    report = pipeline.run(settings, now=now + timedelta(days=1))

    assert report.sources_ok is False
    assert len(load(settings.data_file)["aktuelle"]) == 2
    assert any("nicht erreichbar" in w for w in report.payload["warnings"])


def test_verdaechtiger_einbruch_raeumt_nichts_weg(monkeypatch, settings, now):
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(i) for i in range(4)]})
    pipeline.run(settings, now=now)

    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(0)]})
    report = pipeline.run(settings, now=now + timedelta(days=1))

    assert report.sources_ok is False
    assert len(load(settings.data_file)["aktuelle"]) == 4
    assert any("verdächtig wenig" in w for w in report.payload["warnings"])


def test_zusatzdaten_landen_in_der_datei(monkeypatch, settings, now):
    settings = replace(settings, sources=("anisearch", "anilist"))
    patch_sources(
        monkeypatch,
        scrape_result={"aktuelle": [anime(1, "Cowboy Bebop")]},
        metadata={"cowboy bebop": {
            "genres": ["Action"], "studios": ["Sunrise"], "score": 86,
            "external": {"anilist": 21},
        }},
    )
    report = pipeline.run(settings, now=now)

    assert report.enriched == 1
    entry = load(settings.data_file)["aktuelle"][0]
    assert entry["genres"] == ["Action"]
    assert entry["external"]["anilist"] == 21


def test_news_landen_in_der_datei(monkeypatch, settings, now):
    settings = replace(settings, sources=("anisearch", "news"))
    patch_sources(
        monkeypatch,
        scrape_result={"aktuelle": [anime(1)]},
        news_items=[{
            "title": "Synchro startet", "url": "https://x/1",
            "source": "anime2you.de", "published": iso(now), "summary": "",
        }],
    )
    pipeline.run(settings, now=now)

    data = load(settings.data_file)
    assert data["counts"]["news"] == 1
    assert data["news"][0]["title"] == "Synchro startet"


def test_alte_news_verschwinden_wieder(monkeypatch, settings, now):
    settings = replace(settings, sources=("anisearch", "news"))
    alt = iso(now - timedelta(days=settings.retention.news_max_age_days + 5))
    patch_sources(
        monkeypatch,
        scrape_result={"aktuelle": [anime(1)]},
        news_items=[{"title": "Uralt", "url": "https://x/1", "published": alt}],
    )
    pipeline.run(settings, now=now)
    assert load(settings.data_file)["news"] == []


def test_aufraeumlauf_ohne_scraping(monkeypatch, settings, now):
    """`prune` löscht Altlasten, auch wenn der Scraper gerade klemmt."""
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1), anime(2)]})
    pipeline.run(settings, now=now)

    spaeter = now + timedelta(days=settings.retention.max_age_days + 1)
    report = pipeline.run(settings, now=spaeter, scrape=False)

    assert report.stats.removed_expired == 2
    assert load(settings.data_file)["total"] == 0
    assert report.written is True


def test_aufraeumlauf_setzt_markierungen_nicht_zurueck(monkeypatch, settings, now):
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1), anime(2)]})
    pipeline.run(settings, now=now)
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1)]})
    pipeline.run(settings, now=now + timedelta(days=1))

    pipeline.run(settings, now=now + timedelta(days=2), scrape=False)

    marked = [e for e in load(settings.data_file)["aktuelle"] if e.get("missing_since")]
    assert [e["id"] for e in marked] == [2]


def test_kaputter_filter_fuellt_abgeschlossen(monkeypatch, settings, now):
    """anisearch liefert zweimal dieselbe Liste – wir trennen nach Jahrgang."""
    jahre = [2015, 2019, 2023, 2025, 2026]
    same = [anime(i, f"Titel {i}", f"TV-Serie, 12 ({jahr})") for i, jahr in enumerate(jahre)]
    patch_sources(monkeypatch, scrape_result={
        "kommende": [], "aktuelle": list(same), "abgeschlossen": list(same),
    })

    report = pipeline.run(settings, now=now)
    data = load(settings.data_file)

    assert data["counts"]["abgeschlossen"] > 0
    assert data["counts"]["aktuelle"] > 0
    assert any("Schätzung" in w for w in report.payload["warnings"])
    # Trotzdem steht kein Anime doppelt in der Datei.
    keys = [e["id"] for name in ("kommende", "aktuelle", "abgeschlossen") for e in data[name]]
    assert len(keys) == len(set(keys))


def test_datei_bleibt_fuer_die_website_lesbar(monkeypatch, settings, now):
    """Das Format, das meine-anime-welt.de erwartet, bleibt erhalten."""
    patch_sources(monkeypatch, scrape_result={"aktuelle": [anime(1)]})
    pipeline.run(settings, now=now)

    data = load(settings.data_file)
    for key in ("kommende", "aktuelle", "abgeschlossen", "timestamp", "source", "version"):
        assert key in data

    entry = data["aktuelle"][0]
    for key in ("id", "title", "url", "image", "info", "year", "type", "status"):
        assert key in entry
