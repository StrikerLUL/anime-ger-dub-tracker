# -*- coding: utf-8 -*-
"""Tests der reinen Hilfsfunktionen."""

import pytest

from tests.conftest import anime
from tracker.models import (
    anime_key,
    extract_episodes,
    extract_type,
    extract_year,
    iso,
    normalize_title,
    parse_iso,
    sort_animes,
)


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


@pytest.mark.parametrize("info,expected", [
    ("TV-Serie, 12 (2024)", 12),
    ("Web, 120 (2021)", 120),
    ("Film (2025)", 0),
    ("24 Episoden", 24),
])
def test_extract_episodes(info, expected):
    assert extract_episodes(info) == expected


def test_anime_key_nutzt_id():
    assert anime_key(anime(4711)) == "id:4711"


def test_anime_key_faellt_auf_url_zurueck():
    """Einträge ohne ID dürfen nicht alle auf denselben Schlüssel fallen."""
    a = {"id": 0, "title": "A", "url": "https://www.anisearch.de/anime/a"}
    b = {"id": 0, "title": "B", "url": "https://www.anisearch.de/anime/b"}
    assert anime_key(a) != anime_key(b)


def test_anime_key_faellt_auf_titel_zurueck():
    assert anime_key({"id": 0, "title": "Nur Titel"}) == "title:nur titel"


@pytest.mark.parametrize("left,right", [
    ("Re:Zero – Starting Life", "Re Zero Starting Life"),
    ("FLCL", "flcl"),
    ("Made in Abyss II", "Made in Abyss 2"),
    ("Fruits Basket: The Final", "Fruits Basket The Final"),
])
def test_normalize_title_gleicht_schreibweisen_an(left, right):
    assert normalize_title(left) == normalize_title(right)


def test_normalize_title_wirft_verschiedene_anime_nicht_zusammen():
    assert normalize_title("Attack on Titan") != normalize_title("Attack on Titan: The Final Season")


def test_sort_ist_deterministisch():
    entries = [anime(2, "B", "TV-Serie, 1 (2024)"), anime(1, "A", "TV-Serie, 1 (2026)")]
    assert [a["title"] for a in sort_animes(entries)] == ["A", "B"]
    assert sort_animes(entries) == sort_animes(list(reversed(entries)))


def test_zeitstempel_roundtrip():
    from tracker.models import utcnow
    moment = utcnow()
    assert parse_iso(iso(moment)) == moment


@pytest.mark.parametrize("value", ["", None, "kein datum", 42])
def test_parse_iso_ist_tolerant(value):
    assert parse_iso(value) is None
