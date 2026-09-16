# -*- coding: utf-8 -*-
"""Tests fürs Zusammenführen und Entdoppeln – der ursprüngliche Fehler."""

from tests.conftest import anime
from tracker.merge import (
    attach_metadata,
    dedupe_categories,
    filter_broken,
    split_by_year,
    titles_needing_metadata,
)


def test_kein_anime_steht_in_zwei_kategorien():
    raw = {
        "kommende": [anime(1, "Eins")],
        "aktuelle": [anime(1, "Eins"), anime(2, "Zwei")],
        "abgeschlossen": [anime(2, "Zwei"), anime(3, "Drei")],
    }
    categories, warnings = dedupe_categories(raw)

    assert [a["title"] for a in categories["kommende"]] == ["Eins"]
    assert [a["title"] for a in categories["aktuelle"]] == ["Zwei"]
    assert [a["title"] for a in categories["abgeschlossen"]] == ["Drei"]
    assert any("bereits in" in w for w in warnings)


def test_duplikate_innerhalb_einer_kategorie_fliegen_raus():
    categories, warnings = dedupe_categories({"aktuelle": [anime(1), anime(1), anime(2)]})
    assert len(categories["aktuelle"]) == 2
    assert any("innerhalb der Kategorie" in w for w in warnings)


def test_eintraege_ohne_titel_werden_verworfen():
    categories, _ = dedupe_categories({"aktuelle": [anime(1, ""), anime(2, "Da")]})
    assert [a["title"] for a in categories["aktuelle"]] == ["Da"]


def test_status_wird_gesetzt():
    categories, _ = dedupe_categories({"kommende": [anime(1)]})
    assert categories["kommende"][0]["status"] == "kommende"


def test_identische_filter_ergeben_eine_warnung():
    same = [anime(i) for i in range(10)]
    _, warnings = dedupe_categories({"aktuelle": list(same), "abgeschlossen": list(same)})
    assert filter_broken(warnings)


def test_unterschiedliche_filter_ergeben_keine_warnung():
    _, warnings = dedupe_categories({
        "aktuelle": [anime(i) for i in range(10)],
        "abgeschlossen": [anime(i) for i in range(100, 110)],
    })
    assert not filter_broken(warnings)


def test_jahres_notloesung_fuellt_abgeschlossen():
    """Bei kaputtem Filter wird nach Erscheinungsjahr getrennt statt alles 'aktuell' zu nennen."""
    categories = {
        "kommende": [],
        "aktuelle": [
            anime(1, "Alt", "TV-Serie, 12 (2019)"),
            anime(2, "Neu", "TV-Serie, 12 (2026)"),
        ],
        "abgeschlossen": [],
    }
    result, warnings = split_by_year(categories, current_year=2026)

    assert [a["title"] for a in result["aktuelle"]] == ["Neu"]
    assert [a["title"] for a in result["abgeschlossen"]] == ["Alt"]
    assert result["abgeschlossen"][0]["status"] == "abgeschlossen"
    assert result["abgeschlossen"][0]["status_geschaetzt"] is True
    assert any("Schätzung" in w for w in warnings)


def test_jahres_notloesung_laesst_aktuelle_jahrgaenge_stehen():
    categories = {"aktuelle": [anime(1, "Neu", "TV-Serie, 12 (2025)")]}
    result, warnings = split_by_year(categories, current_year=2026)
    assert len(result["aktuelle"]) == 1
    assert result["abgeschlossen"] == []
    assert warnings == []


def test_zusatzdaten_werden_zugeordnet():
    categories = {"aktuelle": [anime(1, "Cowboy Bebop")], "kommende": [], "abgeschlossen": []}
    metadata = {"cowboy bebop": {
        "genres": ["Action"], "studios": ["Sunrise"], "score": 86,
        "episodes": 26, "external": {"anilist": 1}, "cover": "https://x/cover.webp",
    }}
    assert attach_metadata(categories, metadata) == 1

    entry = categories["aktuelle"][0]
    assert entry["genres"] == ["Action"]
    assert entry["external"]["anilist"] == 1
    # anisearch bleibt die Wahrheit für vorhandene Felder
    assert entry["image"].startswith("https://cdn.anisearch.de/")


def test_zusatzdaten_ohne_treffer_aendern_nichts():
    categories = {"aktuelle": [anime(1, "Cowboy Bebop")], "kommende": [], "abgeschlossen": []}
    before = dict(categories["aktuelle"][0])
    assert attach_metadata(categories, {"ganz anderer anime": {"genres": ["Drama"]}}) == 0
    assert categories["aktuelle"][0] == before


def test_nur_unbekannte_titel_werden_nachgeschlagen():
    categories = {
        "aktuelle": [
            anime(1, "Schon bekannt", genres=["Action"]),
            anime(2, "Noch unbekannt"),
            anime(3, "Auch bekannt", external={"anilist": 5}),
        ],
        "kommende": [], "abgeschlossen": [],
    }
    assert titles_needing_metadata(categories) == ["Noch unbekannt"]
