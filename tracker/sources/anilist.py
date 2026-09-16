#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quelle 2: AniList (https://anilist.co) – kostenlose GraphQL-API, kein API-Key.

Liefert das, was auf den anisearch-Listenseiten fehlt: Episodenzahl, Genres,
Studios, Bewertung, hochauflösendes Cover und die Links zu AniList/MyAnimeList.
Es werden ausschließlich strukturierte Fakten übernommen – keine fremden
Beschreibungstexte.

Höflichkeit: AniList erlaubt 90 Anfragen/Minute. Wir bündeln mehrere Titel per
GraphQL-Alias in eine Anfrage und warten dazwischen.
"""

from __future__ import annotations

import time

from ..http import SourceError, post_json
from ..models import normalize_title

API_URL = "https://graphql.anilist.co"
BATCH_SIZE = 8
PAUSE_SECONDS = 0.8

_FRAGMENT = """
fragment Facts on Media {
  id
  idMal
  title { romaji english native }
  synonyms
  episodes
  genres
  averageScore
  format
  seasonYear
  status
  siteUrl
  coverImage { extraLarge large }
  studios(isMain: true) { nodes { name } }
}
"""

FORMAT_LABELS = {
    "TV": "TV-Serie",
    "TV_SHORT": "TV-Serie",
    "MOVIE": "Film",
    "SPECIAL": "TV-Spezial",
    "OVA": "OVA",
    "ONA": "Web",
    "MUSIC": "Musikvideo",
}


def _build_query(count: int) -> str:
    variables = ", ".join(f"$t{i}: String" for i in range(count))
    aliases = "\n".join(
        f"  a{i}: Media(search: $t{i}, type: ANIME) {{ ...Facts }}" for i in range(count)
    )
    return f"query ({variables}) {{\n{aliases}\n}}\n{_FRAGMENT}"


def _all_titles(media: dict) -> list:
    titles = list((media.get("title") or {}).values())
    titles.extend(media.get("synonyms") or [])
    return [normalize_title(t) for t in titles if t]


def facts_from_media(media: dict) -> dict:
    """AniList-Antwort auf die Felder eindampfen, die der Tracker speichert."""
    studios = [n.get("name") for n in ((media.get("studios") or {}).get("nodes") or []) if n.get("name")]
    cover = media.get("coverImage") or {}
    facts = {
        "external": {"anilist": media.get("id")},
        "genres": [g for g in (media.get("genres") or []) if g][:6],
        "studios": studios[:3],
    }
    if media.get("idMal"):
        facts["external"]["mal"] = media["idMal"]
    if media.get("episodes"):
        facts["episodes"] = int(media["episodes"])
    if media.get("averageScore"):
        facts["score"] = int(media["averageScore"])
    if media.get("seasonYear"):
        facts["season"] = int(media["seasonYear"])
    if media.get("format") in FORMAT_LABELS:
        facts["format_label"] = FORMAT_LABELS[media["format"]]
    if cover.get("extraLarge") or cover.get("large"):
        facts["cover"] = cover.get("extraLarge") or cover.get("large")
    if media.get("siteUrl"):
        facts["external"]["anilist_url"] = media["siteUrl"]
    return facts


def lookup(titles: list, *, timeout: int = 20, budget: int = 240) -> dict:
    """
    Titel bei AniList nachschlagen.

    Rückgabe: {normalisierter Titel: Fakten}. Nur eindeutige Treffer zählen –
    passt der gefundene Titel nicht zum gesuchten, wird er verworfen. Lieber
    kein Genre als das Genre eines fremden Anime.
    """
    wanted = []
    seen = set()
    for title in titles:
        norm = normalize_title(title)
        if norm and norm not in seen:
            seen.add(norm)
            wanted.append(title)
        if len(wanted) >= budget:
            break

    found: dict = {}
    for start in range(0, len(wanted), BATCH_SIZE):
        chunk = wanted[start:start + BATCH_SIZE]
        payload = {
            "query": _build_query(len(chunk)),
            "variables": {f"t{i}": title for i, title in enumerate(chunk)},
        }
        try:
            response = post_json(API_URL, payload, timeout=timeout)
        except SourceError as exc:
            # Teilausfall: was schon da ist, behalten wir.
            print(f"   ⚠️  AniList-Abfrage fehlgeschlagen: {exc}")
            break

        data = response.get("data") or {}
        for index, title in enumerate(chunk):
            media = data.get(f"a{index}")
            if not media:
                continue
            asked = normalize_title(title)
            if asked and asked in _all_titles(media):
                found[asked] = facts_from_media(media)

        if start + BATCH_SIZE < len(wanted):
            time.sleep(PAUSE_SECONDS)

    return found
