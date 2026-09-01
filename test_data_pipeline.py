#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für die Datenlogik des Scrapers.

Läuft ohne Netzwerk und ohne Browser – deshalb kann GitHub Actions die Tests
vor jedem Scraping-Lauf ausführen.

    python -m pytest test_data_pipeline.py -q
"""

import json

import pytest

from anisearch_scraper import (
    CATEGORY_ORDER,
    anime_key,
    build_payload,
    data_hash,
    dedupe_categories,
    extract_type,
    extract_year,
    load_existing,
    write_if_changed,
)


def anime(anime_id, title="Titel", info="TV-Serie, 12 (2024)"):
    return {
        "id": anime_id,
        "title": title,
        "url": f"https://www.anisearch.de/anime/{anime_id},{title.lower()}",
        "image": "",
        "info": info,
        "year": extract_year(info),
        "type": extract_type(info),
    }


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("info,expected", [
    ("TV-Serie, 12 (2024)", 2024),
    ("OVA, 1 (1986)", 1986),
    ("Film (2025)", 2025),
    ("Unbekannt", 0),
    ("", 0),
])
def test_extract_year(info, expected):
    assert extract_year(info) == expected


@pytest.mark.parametrize("info,expected", [
    ("TV-Serie, 12 (2024)", "TV-Serie"),
    ("Film (2025)", "Film"),
    ("OVA, 1 (1986)", "OVA"),
    ("Irgendwas", "Anime"),
])
def test_extract_type(info, expected):
    assert extract_type(info) == expected


def test_anime_key_nutzt_id():
    assert anime_key(anime(4711)) == "id:4711"


def test_anime_key_faellt_auf_url_zurueck():
    """Einträge ohne ID dürfen nicht alle auf denselben Schlüssel fallen."""
    a = {"id": 0, "title": "A", "url": "https://www.anisearch.de/anime/a"}
    b = {"id": 0, "title": "B", "url": "https://www.anisearch.de/anime/b"}
    assert anime_key(a) != anime_key(b)


def test_anime_key_faellt_auf_titel_zurueck():
    a = {"id": 0, "title": "Nur Titel"}
    assert anime_key(a) == "title:nur titel"


# ─── Deduplizierung: der eigentliche Fehler ───────────────────────────────────

def test_kategorien_sind_ueberschneidungsfrei():
    """Derselbe Anime in zwei Kategorien darf nur einmal gespeichert werden."""
    doppelt = [anime(1, "Eins"), anime(2, "Zwei")]
    cats, _ = dedupe_categories({
        "kommende": [],
        "aktuelle": list(doppelt),
        "abgeschlossen": list(doppelt),
    })

    assert len(cats["aktuelle"]) == 2
    assert cats["abgeschlossen"] == []

    alle = [anime_key(a) for entries in cats.values() for a in entries]
    assert len(alle) == len(set(alle))


def test_prioritaet_kommende_vor_aktuelle_vor_abgeschlossen():
    a = anime(1, "Eins")
    cats, _ = dedupe_categories({
        "kommende": [a],
        "aktuelle": [a],
        "abgeschlossen": [a],
    })
    assert [x["title"] for x in cats["kommende"]] == ["Eins"]
    assert cats["aktuelle"] == []
    assert cats["abgeschlossen"] == []
    assert cats["kommende"][0]["status"] == "kommende"


def test_duplikate_innerhalb_einer_kategorie():
    cats, warnings = dedupe_categories({
        "kommende": [anime(1), anime(1), anime(2)],
        "aktuelle": [],
        "abgeschlossen": [],
    })
    assert len(cats["kommende"]) == 2
    assert any("innerhalb der Kategorie" in w for w in warnings)


def test_identische_ergebnismengen_werden_gemeldet():
    """Genau der Fall, der die doppelten Daten verursacht hat."""
    gleich = [anime(i) for i in range(1, 11)]
    _, warnings = dedupe_categories({
        "kommende": [],
        "aktuelle": list(gleich),
        "abgeschlossen": list(gleich),
    })
    assert any("Filter greift nicht" in w for w in warnings)


def test_eintraege_ohne_titel_werden_verworfen():
    cats, _ = dedupe_categories({
        "kommende": [anime(1), {"id": 2, "title": "  "}, {"id": 3}],
        "aktuelle": [],
        "abgeschlossen": [],
    })
    assert len(cats["kommende"]) == 1


def test_unterschiedliche_anime_bleiben_erhalten():
    cats, warnings = dedupe_categories({
        "kommende": [anime(1), anime(2)],
        "aktuelle": [anime(3)],
        "abgeschlossen": [anime(4), anime(5)],
    })
    assert sum(len(v) for v in cats.values()) == 5
    assert not any("Filter greift nicht" in w for w in warnings)


# ─── Hash & Schreiben ─────────────────────────────────────────────────────────

def test_hash_ist_reihenfolgeunabhaengig_stabil():
    a, b = anime(1), anime(2)
    cats1, _ = dedupe_categories({"kommende": [a, b], "aktuelle": [], "abgeschlossen": []})
    cats2, _ = dedupe_categories({"kommende": [b, a], "aktuelle": [], "abgeschlossen": []})
    assert data_hash(cats1) == data_hash(cats2)


def test_hash_aendert_sich_bei_neuem_anime():
    cats1, _ = dedupe_categories({"kommende": [anime(1)], "aktuelle": [], "abgeschlossen": []})
    cats2, _ = dedupe_categories({"kommende": [anime(1), anime(2)], "aktuelle": [], "abgeschlossen": []})
    assert data_hash(cats1) != data_hash(cats2)


def test_datei_wird_bei_gleichen_daten_nicht_neu_geschrieben(tmp_path):
    """Kernpunkt gegen die endlos wachsende Historie."""
    path = str(tmp_path / "anime_data.json")
    cats, _ = dedupe_categories({"kommende": [anime(1)], "aktuelle": [], "abgeschlossen": []})

    written_first, _ = write_if_changed(cats, path=path)
    inhalt_vorher = open(path, encoding="utf-8").read()

    written_second, _ = write_if_changed(cats, path=path)
    inhalt_nachher = open(path, encoding="utf-8").read()

    assert written_first is True
    assert written_second is False
    assert inhalt_vorher == inhalt_nachher


def test_datei_wird_bei_geaenderten_daten_geschrieben(tmp_path):
    path = str(tmp_path / "anime_data.json")
    cats1, _ = dedupe_categories({"kommende": [anime(1)], "aktuelle": [], "abgeschlossen": []})
    cats2, _ = dedupe_categories({"kommende": [anime(1), anime(2)], "aktuelle": [], "abgeschlossen": []})

    write_if_changed(cats1, path=path)
    written, payload = write_if_changed(cats2, path=path)

    assert written is True
    assert payload["total"] == 2


def test_zeitstempel_bleibt_bei_unveraenderten_daten_stehen(tmp_path):
    path = str(tmp_path / "anime_data.json")
    cats, _ = dedupe_categories({"kommende": [anime(1)], "aktuelle": [], "abgeschlossen": []})

    _, erst = write_if_changed(cats, path=path)
    _, wieder = write_if_changed(cats, path=path)

    assert wieder["data_changed_at"] == erst["data_changed_at"]


def test_payload_behaelt_alte_schluessel_bei(tmp_path):
    """Rückwärtskompatibilität: meine-anime-welt.de liest diese Felder."""
    cats, _ = dedupe_categories({"kommende": [anime(1)], "aktuelle": [], "abgeschlossen": []})
    payload = build_payload(cats)

    for key in list(CATEGORY_ORDER) + ["timestamp", "source", "version"]:
        assert key in payload
    assert isinstance(payload["kommende"], list)


def test_geschriebene_datei_ist_gueltiges_json(tmp_path):
    path = str(tmp_path / "anime_data.json")
    cats, warnings = dedupe_categories({
        "kommende": [anime(1, "Ä Umlaut-Titel")],
        "aktuelle": [],
        "abgeschlossen": [],
    })
    write_if_changed(cats, warnings=warnings, path=path)

    data = json.loads(open(path, encoding="utf-8").read())
    assert data["kommende"][0]["title"] == "Ä Umlaut-Titel"
    assert load_existing(path) == data


def test_load_existing_bei_defekter_datei(tmp_path):
    path = tmp_path / "kaputt.json"
    path.write_text("{kein gültiges json", encoding="utf-8")
    assert load_existing(str(path)) == {}


# ─── Ausgelieferte Datendatei ────────────────────────────────────────────────

def test_ausgelieferte_datei_hat_keine_duplikate():
    """anime_data.json im Repo muss frei von Duplikaten sein."""
    from anisearch_scraper import DATA_FILE

    data = load_existing(DATA_FILE)
    if not data:
        pytest.skip("anime_data.json nicht vorhanden")

    keys = [anime_key(a) for name in CATEGORY_ORDER for a in data.get(name, [])]
    doppelte = {k for k in keys if keys.count(k) > 1}
    assert not doppelte, f"Doppelte Anime in anime_data.json: {sorted(doppelte)[:5]}"
