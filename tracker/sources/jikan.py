#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quelle 3: Jikan (https://jikan.moe) – die offene MyAnimeList-API, ebenfalls
ohne API-Key.

Springt nur dort ein, wo AniList nichts gefunden hat. Das hält die Anzahl der
Anfragen klein (Jikan erlaubt 3 Anfragen/Sekunde, 60/Minute) und bleibt höflich.
Auch hier werden nur strukturierte Fakten übernommen.
"""

from __future__ import annotations

import time
import urllib.parse

from ..http import SourceError, get_json
from ..models import normalize_title

API_URL = "https://api.jikan.moe/v4/anime"
PAUSE_SECONDS = 0.6

FORMAT_LABELS = {
    "TV": "TV-Serie",
    "Movie": "Film",
    "OVA": "OVA",
    "ONA": "Web",
    "Special": "TV-Spezial",
    "Music": "Musikvideo",
}


def _all_titles(media: dict) -> list:
    values = [media.get("title"), media.get("title_english"), media.get("title_japanese")]
    values.extend(media.get("title_synonyms") or [])
    for entry in media.get("titles") or []:
        values.append(entry.get("title"))
    return [normalize_title(v) for v in values if v]


def facts_from_media(media: dict) -> dict:
    """Jikan-Antwort auf die Felder eindampfen, die der Tracker speichert."""
    facts = {
        "external": {"mal": media.get("mal_id")},
        "genres": [g.get("name") for g in (media.get("genres") or []) if g.get("name")][:6],
        "studios": [s.get("name") for s in (media.get("studios") or []) if s.get("name")][:3],
    }
    if media.get("episodes"):
        facts["episodes"] = int(media["episodes"])
    if media.get("score"):
        facts["score"] = int(round(float(media["score"]) * 10))
    if (media.get("aired") or {}).get("prop", {}).get("from", {}).get("year"):
        facts["season"] = int(media["aired"]["prop"]["from"]["year"])
    if media.get("type") in FORMAT_LABELS:
        facts["format_label"] = FORMAT_LABELS[media["type"]]
    image = ((media.get("images") or {}).get("webp") or {}).get("large_image_url") \
        or ((media.get("images") or {}).get("jpg") or {}).get("large_image_url")
    if image:
        facts["cover"] = image
    if media.get("url"):
        facts["external"]["mal_url"] = media["url"]
    return facts


def lookup(titles: list, *, timeout: int = 20, budget: int = 30) -> dict:
    """
    Titel bei MyAnimeList nachschlagen (ein Aufruf je Titel, daher knappes Budget).

    Rückgabe: {normalisierter Titel: Fakten} – nur bei eindeutigem Titeltreffer.
    """
    found: dict = {}
    asked: set = set()

    for title in titles:
        norm = normalize_title(title)
        if not norm or norm in asked:
            continue
        asked.add(norm)
        if len(asked) > budget:
            break

        query = urllib.parse.urlencode({"q": title, "limit": 3, "sfw": "true"})
        try:
            response = get_json(f"{API_URL}?{query}", timeout=timeout, retries=1)
        except SourceError as exc:
            print(f"   ⚠️  Jikan-Abfrage fehlgeschlagen: {exc}")
            break

        for media in response.get("data") or []:
            if norm in _all_titles(media):
                found[norm] = facts_from_media(media)
                break

        time.sleep(PAUSE_SECONDS)

    return found
