# -*- coding: utf-8 -*-
"""
Tests der Qualitätsprüfung.

`check` ist die letzte Station vor der Website – was hier durchrutscht, sehen
die Besucher. Deshalb: für jede Fehlerart ein Test.
"""

import json
from datetime import timedelta

from tests.conftest import anime
from tracker.check import check, collect_problems
from tracker.models import iso
from tracker.store import build_payload


def datei(tmp_path, payload):
    path = tmp_path / "anime_data.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def gueltig(now, entries=None):
    categories = {
        "kommende": [],
        "aktuelle": entries if entries is not None else [dict(
            anime(1), status="aktuelle", first_seen=iso(now - timedelta(days=5)),
            expires_at=iso(now + timedelta(days=360)),
        )],
        "abgeschlossen": [],
    }
    return build_payload(categories, now=now)


def test_gute_datei_geht_durch(tmp_path, now):
    assert check(datei(tmp_path, gueltig(now)), now=now) == 0


def test_fehlende_datei_faellt_durch(tmp_path):
    assert check(str(tmp_path / "gibtsnicht.json")) == 1


def test_kaputtes_json_faellt_durch(tmp_path):
    path = tmp_path / "anime_data.json"
    path.write_text("{kein json", encoding="utf-8")
    assert check(str(path)) == 1


def test_leere_datei_faellt_durch(tmp_path, now):
    assert check(datei(tmp_path, gueltig(now, entries=[])), now=now) == 1


def test_duplikat_ueber_kategorien_faellt_durch(now):
    payload = gueltig(now)
    payload["kommende"] = list(payload["aktuelle"])
    errors, _ = collect_problems(payload, now=now)
    assert any("sowohl in" in e for e in errors)


def test_duplikat_innerhalb_einer_kategorie_faellt_durch(now):
    payload = gueltig(now)
    payload["aktuelle"] = payload["aktuelle"] * 2
    errors, _ = collect_problems(payload, now=now)
    assert any("doppelt" in e for e in errors)


def test_eintrag_ohne_link_faellt_durch(now):
    payload = gueltig(now)
    payload["aktuelle"][0]["url"] = ""
    errors, _ = collect_problems(payload, now=now)
    assert any("keinen Link" in e for e in errors)


def test_falsche_counts_fallen_durch(now):
    payload = gueltig(now)
    payload["counts"]["aktuelle"] = 99
    errors, _ = collect_problems(payload, now=now)
    assert any("counts" in e for e in errors)


def test_falscher_hash_faellt_durch(now):
    payload = gueltig(now)
    payload["data_hash"] = "0" * 64
    errors, _ = collect_problems(payload, now=now)
    assert any("data_hash" in e for e in errors)


def test_abgelaufener_eintrag_faellt_durch(now):
    payload = gueltig(now)
    payload["aktuelle"][0]["expires_at"] = iso(now - timedelta(days=1))
    errors, _ = collect_problems(payload, now=now)
    assert any("abgelaufen" in e for e in errors)


def test_zu_lange_vermisster_eintrag_faellt_durch(now, policy):
    payload = gueltig(now)
    payload["aktuelle"][0]["missing_since"] = iso(now - timedelta(days=policy.stale_grace_days + 5))
    errors, _ = collect_problems(payload, now=now, policy=policy)
    assert any("hätte gelöscht sein müssen" in e for e in errors)


def test_zu_alte_news_fallen_durch(now, policy):
    payload = gueltig(now)
    payload["news"] = [{
        "title": "Uralt", "url": "https://x/1",
        "published": iso(now - timedelta(days=policy.news_max_age_days + 5)),
    }]
    errors, _ = collect_problems(payload, now=now, policy=policy)
    assert any("zu alt" in e for e in errors)


def test_fehlendes_bild_ist_nur_ein_hinweis(tmp_path, now):
    ohne_bild = dict(
        anime(1), image="", status="aktuelle",
        first_seen=iso(now - timedelta(days=5)), expires_at=iso(now + timedelta(days=360)),
    )
    payload = gueltig(now, entries=[ohne_bild])
    errors, hints = collect_problems(payload, now=now)
    assert errors == []
    assert any("ohne Coverbild" in h for h in hints)
    assert check(datei(tmp_path, payload), now=now) == 0


def test_scraper_warnungen_sind_hinweise(now):
    payload = gueltig(now)
    payload["warnings"] = ["Filter greift nicht: ..."]
    errors, hints = collect_problems(payload, now=now)
    assert errors == []
    assert "Filter greift nicht: ..." in hints
