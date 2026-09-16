# -*- coding: utf-8 -*-
"""Tests fürs Schreiben von anime_data.json."""

import json
from datetime import timedelta

from tests.conftest import anime
from tracker.config import CATEGORY_ORDER, DATA_VERSION
from tracker.store import build_payload, data_hash, load, write_if_changed


def categories(*entries):
    data = {name: [] for name in CATEGORY_ORDER}
    data["aktuelle"] = list(entries)
    return data


def test_payload_behaelt_die_alten_felder(now):
    payload = build_payload(categories(anime(1)), now=now)

    for key in ("kommende", "aktuelle", "abgeschlossen", "timestamp", "source", "version"):
        assert key in payload, f"{key} fehlt – bestehende Einbindungen würden brechen"
    assert payload["source"] == "anisearch.de"
    assert payload["version"] == DATA_VERSION
    assert payload["total"] == 1
    assert payload["counts"]["aktuelle"] == 1


def test_payload_enthaelt_die_aufbewahrungsregeln(now, policy):
    payload = build_payload(categories(anime(1)), retention=policy, now=now)
    assert payload["retention"]["max_age_days"] == policy.max_age_days
    assert payload["retention"]["stale_grace_days"] == policy.stale_grace_days


def test_hash_ignoriert_buchhaltung(now):
    plain = categories(anime(1))
    with_bookkeeping = categories(dict(
        anime(1), first_seen="2026-01-01T00:00:00Z",
        expires_at="2027-01-01T00:00:00Z", missing_since="2026-09-01T00:00:00Z",
        status="aktuelle",
    ))
    assert data_hash(plain) == data_hash(with_bookkeeping)


def test_hash_reagiert_auf_echte_aenderungen():
    assert data_hash(categories(anime(1))) != data_hash(categories(anime(1, "Anderer Titel")))


def test_zeitstempel_bleibt_stehen_wenn_sich_nichts_aendert(now):
    first = build_payload(categories(anime(1)), now=now)
    later = build_payload(categories(anime(1)), previous=first, now=now + timedelta(days=3))
    assert later["timestamp"] == first["timestamp"]


def test_zeitstempel_springt_bei_echter_aenderung(now):
    first = build_payload(categories(anime(1)), now=now)
    later = build_payload(categories(anime(2)), previous=first, now=now + timedelta(days=3))
    assert later["timestamp"] != first["timestamp"]


def test_datei_bleibt_bei_gleichen_daten_byte_fuer_byte_gleich(tmp_path, now):
    path = str(tmp_path / "anime_data.json")

    payload = build_payload(categories(anime(1)), now=now)
    assert write_if_changed(payload, path, now=now) is True
    before = open(path, "rb").read()

    previous = load(path)
    again = build_payload(categories(anime(1)), previous=previous, now=now + timedelta(days=1))
    assert write_if_changed(again, path, now=now + timedelta(days=1)) is False
    assert open(path, "rb").read() == before


def test_aenderung_wird_geschrieben(tmp_path, now):
    path = str(tmp_path / "anime_data.json")
    write_if_changed(build_payload(categories(anime(1)), now=now), path, now=now)

    previous = load(path)
    payload = build_payload(categories(anime(1), anime(2)), previous=previous, now=now)
    assert write_if_changed(payload, path, now=now) is True
    assert load(path)["total"] == 2


def test_geloeschte_karteileiche_fuehrt_zum_schreiben(tmp_path, now):
    """Auch wenn der Anime-Hash gleich bleibt: verschwundene Einträge müssen raus."""
    path = str(tmp_path / "anime_data.json")
    entry = dict(anime(1), first_seen="2026-01-01T00:00:00Z")

    write_if_changed(build_payload(categories(entry), now=now), path, now=now)
    previous = load(path)

    marked = dict(entry, missing_since="2026-09-10T00:00:00Z")
    payload = build_payload(categories(marked), previous=previous, now=now)
    assert data_hash(categories(marked)) == previous["data_hash"]
    assert write_if_changed(payload, path, now=now) is True


def test_datei_ist_gueltiges_utf8_json(tmp_path, now):
    path = str(tmp_path / "anime_data.json")
    write_if_changed(build_payload(categories(anime(1, "Kimi ni Todoke – Nähe")), now=now), path, now=now)

    raw = open(path, "r", encoding="utf-8").read()
    assert raw.endswith("\n")
    assert "Nähe" in raw            # keine \u-Escapes
    assert json.loads(raw)["total"] == 1


def test_keine_temporaere_datei_bleibt_liegen(tmp_path, now):
    path = str(tmp_path / "anime_data.json")
    write_if_changed(build_payload(categories(anime(1)), now=now), path, now=now)
    assert not (tmp_path / "anime_data.json.tmp").exists()


def test_load_ist_tolerant(tmp_path):
    assert load(str(tmp_path / "gibtsnicht.json")) == {}
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    assert load(str(kaputt)) == {}
