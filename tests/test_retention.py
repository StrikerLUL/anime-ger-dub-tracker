# -*- coding: utf-8 -*-
"""
Tests der Aufbewahrung – das Herzstück von "Daten liegen nicht ewig herum".
"""

from datetime import timedelta

from tests.conftest import anime
from tracker import retention
from tracker.models import iso
from tracker.retention import prune_news


def payload(categories, retired=None):
    data = {"kommende": [], "aktuelle": [], "abgeschlossen": []}
    data.update(categories)
    if retired:
        data["retired"] = retired
    return data


def test_neuer_eintrag_bekommt_erstsichtung_und_verfallsdatum(now, policy):
    fresh = {"aktuelle": [anime(1)]}
    categories, _retired, stats = retention.apply(fresh, {}, now=now, policy=policy)

    entry = categories["aktuelle"][0]
    assert entry["first_seen"] == iso(now)
    assert entry["expires_at"] == iso(now + timedelta(days=policy.max_age_days))
    assert stats.added == 1


def test_erstsichtung_bleibt_bei_wiedersehen_erhalten(now, policy):
    first = iso(now - timedelta(days=100))
    previous = payload({"aktuelle": [dict(anime(1), first_seen=first)]})

    categories, _retired, stats = retention.apply(
        {"aktuelle": [anime(1)]}, previous, now=now, policy=policy
    )
    assert categories["aktuelle"][0]["first_seen"] == first
    assert stats.added == 0 and stats.kept == 1


def test_verschwundener_eintrag_wird_zuerst_nur_markiert(now, policy):
    previous = payload({"aktuelle": [dict(anime(1), first_seen=iso(now - timedelta(days=5)))]})

    categories, _retired, stats = retention.apply({"aktuelle": []}, previous, now=now, policy=policy)

    assert len(categories["aktuelle"]) == 1
    assert categories["aktuelle"][0]["missing_since"] == iso(now)
    assert stats.missing == 1 and stats.removed_stale == 0


def test_verschwundener_eintrag_wird_nach_der_karenz_geloescht(now, policy):
    gone_since = iso(now - timedelta(days=policy.stale_grace_days + 1))
    previous = payload({"aktuelle": [
        dict(anime(1), first_seen=iso(now - timedelta(days=60)), missing_since=gone_since)
    ]})

    categories, _retired, stats = retention.apply({"aktuelle": []}, previous, now=now, policy=policy)

    assert categories["aktuelle"] == []
    assert stats.removed_stale == 1


def test_rueckkehr_loescht_die_markierung(now, policy):
    previous = payload({"aktuelle": [dict(
        anime(1), first_seen=iso(now - timedelta(days=30)), missing_since=iso(now - timedelta(days=2))
    )]})

    categories, _retired, stats = retention.apply(
        {"aktuelle": [anime(1)]}, previous, now=now, policy=policy
    )
    assert "missing_since" not in categories["aktuelle"][0]
    assert stats.returned == 1


def test_hoechstalter_loescht_und_sperrt(now, policy):
    old = iso(now - timedelta(days=policy.max_age_days + 1))
    previous = payload({"aktuelle": [dict(anime(1), first_seen=old)]})

    categories, retired, stats = retention.apply(
        {"aktuelle": [anime(1)]}, previous, now=now, policy=policy
    )

    assert categories["aktuelle"] == []
    assert stats.removed_expired == 1
    assert "id:1" in retired


def test_gesperrter_eintrag_kommt_nicht_sofort_zurueck(now, policy):
    retired = {"id:1": iso(now + timedelta(days=30))}
    categories, still_retired, stats = retention.apply(
        {"aktuelle": [anime(1)]}, payload({}, retired), now=now, policy=policy
    )

    assert categories["aktuelle"] == []
    assert stats.skipped_blocked == 1
    assert "id:1" in still_retired


def test_abgelaufene_sperre_laesst_den_anime_wieder_zu(now, policy):
    retired = {"id:1": iso(now - timedelta(days=1))}
    categories, still_retired, stats = retention.apply(
        {"aktuelle": [anime(1)]}, payload({}, retired), now=now, policy=policy
    )

    assert len(categories["aktuelle"]) == 1
    assert still_retired == {}
    assert stats.tombstones_expired == 1


def test_obergrenze_je_kategorie(now, policy):
    fresh = {"aktuelle": [anime(i, f"Titel {i:02d}", f"TV-Serie, 12 ({2000 + i})") for i in range(12)]}
    categories, _retired, stats = retention.apply(fresh, {}, now=now, policy=policy)

    assert len(categories["aktuelle"]) == policy.max_entries_per_category
    assert stats.removed_capped == 12 - policy.max_entries_per_category
    # Die neuesten Jahrgänge überleben.
    assert categories["aktuelle"][0]["year"] == 2011


def test_gestoerte_quelle_raeumt_nichts_weg(now, policy):
    """Ein Netzwerkausfall darf die Website nicht leerräumen."""
    previous = payload({"aktuelle": [
        dict(anime(i), first_seen=iso(now - timedelta(days=10))) for i in range(3)
    ]})

    categories, _retired, stats = retention.apply(
        {"aktuelle": []}, previous, now=now, policy=policy, sources_ok=False
    )

    assert len(categories["aktuelle"]) == 3
    assert stats.missing == 0 and stats.removed_stale == 0
    assert all("missing_since" not in a for a in categories["aktuelle"])


def test_hoechstalter_greift_auch_bei_gestoerter_quelle(now, policy):
    previous = payload({"aktuelle": [
        dict(anime(1), first_seen=iso(now - timedelta(days=policy.max_age_days + 5)))
    ]})
    categories, _retired, stats = retention.apply(
        {}, previous, now=now, policy=policy, sources_ok=False
    )
    assert categories["aktuelle"] == []
    assert stats.removed_expired == 1


def test_angereicherte_felder_ueberleben_den_naechsten_lauf(now, policy):
    previous = payload({"aktuelle": [dict(
        anime(1), first_seen=iso(now - timedelta(days=3)),
        genres=["Action"], studios=["Sunrise"], external={"anilist": 7}, episodes=26,
    )]})

    categories, _retired, _stats = retention.apply(
        {"aktuelle": [anime(1)]}, previous, now=now, policy=policy
    )

    entry = categories["aktuelle"][0]
    assert entry["genres"] == ["Action"]
    assert entry["external"] == {"anilist": 7}
    assert entry["episodes"] == 26


def test_kategoriewechsel_erzeugt_keinen_zweiten_eintrag(now, policy):
    previous = payload({"kommende": [dict(anime(1), first_seen=iso(now - timedelta(days=20)))]})
    categories, _retired, _stats = retention.apply(
        {"aktuelle": [anime(1)]}, previous, now=now, policy=policy
    )

    assert categories["kommende"] == []
    assert len(categories["aktuelle"]) == 1
    assert categories["aktuelle"][0]["status"] == "aktuelle"


def test_news_werden_nach_alter_und_menge_gekuerzt(now, policy):
    news = [
        {"title": "neu", "url": "a", "published": iso(now)},
        {"title": "mittel", "url": "b", "published": iso(now - timedelta(days=5))},
        {"title": "alt", "url": "c", "published": iso(now - timedelta(days=40))},
        {"title": "auch neu", "url": "d", "published": iso(now - timedelta(days=1))},
        {"title": "ebenfalls", "url": "e", "published": iso(now - timedelta(days=2))},
    ]
    kept = prune_news(news, now=now, policy=policy)

    assert len(kept) == policy.news_max_items
    assert [n["title"] for n in kept] == ["neu", "auch neu", "ebenfalls"]
