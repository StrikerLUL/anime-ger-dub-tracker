#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quelle 4: deutsche Anime-News-Feeds (RSS/Atom).

Liefert keine Anime-Einträge, sondern Meldungen zu neuen Synchronisationen –
auf der Website wird daraus ein kleiner News-Bereich. Es werden nur Titel,
Link, Datum und Quelle gespeichert, keine fremden Artikeltexte.

Feeds, die nicht antworten oder kein gültiges XML liefern, werden still
übersprungen: eine News-Panne darf die Anime-Daten nicht gefährden.
"""

from __future__ import annotations

import html
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from xml.etree import ElementTree

from ..config import NEWS_KEYWORDS
from ..http import SourceError, get_text
from ..models import iso, parse_iso, utcnow

_TAG = re.compile(r"<[^>]+>")
_ATOM = "{http://www.w3.org/2005/Atom}"


def _clean(text: str, limit: int = 180) -> str:
    """Markup entfernen, Entities auflösen, auf eine Zeile kürzen."""
    plain = html.unescape(_TAG.sub(" ", text or ""))
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:limit].rstrip() + "…" if len(plain) > limit else plain


def _date(value: str):
    """RSS (RFC 822) und Atom (ISO 8601) verstehen."""
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return parse_iso(value)


def _feed_name(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def parse_feed(xml_text: str, feed_url: str) -> list:
    """Ein RSS- oder Atom-Dokument in eine Liste von News-Einträgen übersetzen."""
    try:
        root = ElementTree.fromstring(xml_text.strip())
    except ElementTree.ParseError as exc:
        raise SourceError(f"Kein gültiges XML: {exc}") from exc

    items = root.findall(".//item") or root.findall(f".//{_ATOM}entry")
    source = _feed_name(feed_url)
    entries = []

    for item in items:
        title_el = item.find("title")
        if title_el is None:
            title_el = item.find(f"{_ATOM}title")
        title = _clean(title_el.text if title_el is not None else "", 160)
        if not title:
            continue

        link_el = item.find("link")
        link = ""
        if link_el is not None:
            link = (link_el.text or "").strip()
        if not link:
            atom_link = item.find(f"{_ATOM}link")
            if atom_link is not None:
                link = (atom_link.get("href") or "").strip()
        if not link.startswith("http"):
            continue

        published = None
        for tag in ("pubDate", "{http://purl.org/dc/elements/1.1/}date",
                    f"{_ATOM}updated", f"{_ATOM}published"):
            el = item.find(tag)
            if el is not None and el.text:
                published = _date(el.text)
                if published:
                    break

        summary_el = item.find("description")
        if summary_el is None:
            summary_el = item.find(f"{_ATOM}summary")
        summary = _clean(summary_el.text if summary_el is not None else "")

        entries.append({
            "title": title,
            "url": link,
            "source": source,
            "published": iso(published) if published else "",
            "summary": summary,
        })

    return entries


def is_relevant(entry: dict) -> bool:
    """Nur Meldungen mit Synchro-Bezug – der Tracker ist kein News-Reader."""
    haystack = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
    return any(word in haystack for word in NEWS_KEYWORDS)


def fetch(feeds, *, timeout: int = 20, max_items: int = 40, max_age_days: int = 30) -> list:
    """
    Alle Feeds einlesen, filtern, entdoppeln und auf die neuesten Meldungen kürzen.
    """
    now = utcnow()
    collected: dict = {}

    for feed_url in feeds:
        try:
            xml_text = get_text(feed_url, timeout=timeout, retries=1)
            entries = parse_feed(xml_text, feed_url)
        except SourceError as exc:
            print(f"   ⚠️  News-Feed übersprungen ({feed_url}): {exc}")
            continue
        except Exception as exc:                    # noqa: BLE001 – Feeds sind wild
            print(f"   ⚠️  News-Feed fehlerhaft ({feed_url}): {exc}")
            continue

        for entry in entries:
            if not is_relevant(entry):
                continue
            published = parse_iso(entry["published"])
            if published and (now - published).days > max_age_days:
                continue
            collected.setdefault(entry["url"], entry)

    ordered = sorted(
        collected.values(),
        key=lambda e: (e.get("published") or "", e.get("title", "")),
        reverse=True,
    )
    return ordered[:max_items]
