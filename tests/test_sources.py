# -*- coding: utf-8 -*-
"""
Tests der Quellen – ohne Netzwerk.

Geprüft wird das, was wir selbst verantworten: das Übersetzen der Antworten in
unser Datenmodell, der Titelabgleich und die Fehlertoleranz.
"""

import pytest

from tracker.http import SourceError
from tracker.sources import anilist, jikan, news
from tracker.sources.base import run_source

# ─── AniList ──────────────────────────────────────────────────────────────────

MEDIA = {
    "id": 21, "idMal": 30,
    "title": {"romaji": "Cowboy Bebop", "english": "Cowboy Bebop", "native": "カウボーイビバップ"},
    "synonyms": ["COWBOY BEBOP"],
    "episodes": 26, "genres": ["Action", "Sci-Fi"], "averageScore": 86,
    "format": "TV", "seasonYear": 1998, "status": "FINISHED",
    "siteUrl": "https://anilist.co/anime/21",
    "coverImage": {"extraLarge": "https://img/xl.jpg", "large": "https://img/l.jpg"},
    "studios": {"nodes": [{"name": "Sunrise"}]},
}


def test_anilist_uebersetzt_die_antwort():
    facts = anilist.facts_from_media(MEDIA)
    assert facts["episodes"] == 26
    assert facts["genres"] == ["Action", "Sci-Fi"]
    assert facts["studios"] == ["Sunrise"]
    assert facts["score"] == 86
    assert facts["cover"] == "https://img/xl.jpg"
    assert facts["external"] == {
        "anilist": 21, "mal": 30, "anilist_url": "https://anilist.co/anime/21",
    }


def test_anilist_speichert_keine_fremdtexte():
    """Wir übernehmen Fakten, keine fremden Beschreibungstexte."""
    facts = anilist.facts_from_media({**MEDIA, "description": "Langer Text"})
    assert "description" not in facts


def test_anilist_nimmt_nur_eindeutige_treffer(monkeypatch):
    def fake_post(url, payload, **kwargs):
        return {"data": {"a0": MEDIA, "a1": MEDIA}}

    monkeypatch.setattr(anilist, "post_json", fake_post)
    found = anilist.lookup(["Cowboy Bebop", "Ein ganz anderer Anime"])

    assert "cowboy bebop" in found
    assert "ein ganz anderer anime" not in found, "falscher Treffer darf nicht übernommen werden"


def test_anilist_ueberlebt_einen_ausfall(monkeypatch):
    def boom(*args, **kwargs):
        raise SourceError("503")

    monkeypatch.setattr(anilist, "post_json", boom)
    assert anilist.lookup(["Irgendwas"]) == {}


def test_anilist_haelt_sein_budget_ein(monkeypatch):
    calls = []

    def fake_post(url, payload, **kwargs):
        calls.append(len(payload["variables"]))
        return {"data": {}}

    monkeypatch.setattr(anilist, "post_json", fake_post)
    monkeypatch.setattr(anilist, "PAUSE_SECONDS", 0)
    anilist.lookup([f"Titel {i}" for i in range(50)], budget=10)

    assert sum(calls) == 10


# ─── Jikan ────────────────────────────────────────────────────────────────────

JIKAN_MEDIA = {
    "mal_id": 30, "title": "Cowboy Bebop", "titles": [{"title": "Cowboy Bebop"}],
    "episodes": 26, "score": 8.75, "type": "TV",
    "genres": [{"name": "Action"}], "studios": [{"name": "Sunrise"}],
    "images": {"webp": {"large_image_url": "https://img/mal.webp"}},
    "aired": {"prop": {"from": {"year": 1998}}},
    "url": "https://myanimelist.net/anime/1",
}


def test_jikan_uebersetzt_die_antwort():
    facts = jikan.facts_from_media(JIKAN_MEDIA)
    assert facts["episodes"] == 26
    assert facts["score"] == 88          # 8.75 → 88 (gleiche Skala wie AniList)
    assert facts["external"]["mal"] == 30


def test_jikan_nimmt_nur_titeltreffer(monkeypatch):
    monkeypatch.setattr(jikan, "get_json", lambda url, **kw: {"data": [JIKAN_MEDIA]})
    monkeypatch.setattr(jikan, "PAUSE_SECONDS", 0)

    assert "cowboy bebop" in jikan.lookup(["Cowboy Bebop"])
    assert jikan.lookup(["Etwas völlig anderes"]) == {}


def test_jikan_ueberlebt_einen_ausfall(monkeypatch):
    def boom(*args, **kwargs):
        raise SourceError("429")

    monkeypatch.setattr(jikan, "get_json", boom)
    assert jikan.lookup(["Irgendwas"]) == {}


# ─── News ─────────────────────────────────────────────────────────────────────

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Neue deutsche Synchro f&#252;r Anime XY</title>
    <link>https://www.anime2you.de/news/1/</link>
    <pubDate>Mon, 15 Sep 2026 10:00:00 +0200</pubDate>
    <description>&lt;p&gt;Der Dub startet im Oktober.&lt;/p&gt;</description>
  </item>
  <item>
    <title>Neuer Manga-Band angek&#252;ndigt</title>
    <link>https://www.anime2you.de/news/2/</link>
    <pubDate>Mon, 15 Sep 2026 09:00:00 +0200</pubDate>
    <description>Ohne Bezug</description>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Deutscher Dub bestätigt</title>
    <link href="https://example.de/atom-1"/>
    <updated>2026-09-14T08:30:00Z</updated>
    <summary>Sprecher stehen fest.</summary>
  </entry>
</feed>"""


def test_rss_wird_gelesen():
    items = news.parse_feed(RSS, "https://www.anime2you.de/feed/")
    assert len(items) == 2
    assert items[0]["title"] == "Neue deutsche Synchro für Anime XY"
    assert items[0]["source"] == "anime2you.de"
    assert items[0]["published"] == "2026-09-15T08:00:00Z"
    assert items[0]["summary"] == "Der Dub startet im Oktober."


def test_atom_wird_gelesen():
    items = news.parse_feed(ATOM, "https://example.de/feed")
    assert items[0]["url"] == "https://example.de/atom-1"
    assert items[0]["published"] == "2026-09-14T08:30:00Z"


def test_nur_synchro_meldungen_zaehlen():
    items = news.parse_feed(RSS, "https://www.anime2you.de/feed/")
    assert news.is_relevant(items[0]) is True
    assert news.is_relevant(items[1]) is False


def test_kaputtes_xml_wirft_sourceerror():
    with pytest.raises(SourceError):
        news.parse_feed("<rss><kaputt>", "https://example.de/feed")


def test_fetch_ueberspringt_tote_feeds(monkeypatch):
    def fake_get(url, **kwargs):
        if "tot" in url:
            raise SourceError("404")
        return RSS

    monkeypatch.setattr(news, "get_text", fake_get)
    items = news.fetch(
        ["https://tot.example/feed", "https://www.anime2you.de/feed/"],
        max_age_days=100000,
    )
    assert len(items) == 1


def test_fetch_entdoppelt_ueber_feeds_hinweg(monkeypatch):
    monkeypatch.setattr(news, "get_text", lambda url, **kw: RSS)
    items = news.fetch(["https://a/feed", "https://b/feed"], max_age_days=100000)
    assert len(items) == 1


# ─── Fehlerkapselung ──────────────────────────────────────────────────────────

def test_run_source_faengt_jeden_fehler():
    result, report = run_source("kaputt", lambda: 1 / 0)
    assert result is None
    assert report.ok is False
    assert "ZeroDivisionError" in report.error


def test_run_source_zaehlt_treffer():
    _result, report = run_source("liste", lambda: [1, 2, 3])
    assert report.ok and report.items == 3

    _result, report = run_source("dict", lambda: {"a": [1, 2], "b": [3]})
    assert report.items == 3
