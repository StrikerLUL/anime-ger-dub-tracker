#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kleiner HTTP-Helfer für die JSON- und RSS-Quellen.

Bewusst nur mit der Standardbibliothek: der Scraper soll ohne zusätzliche
Abhängigkeiten laufen (Playwright und Flask sind schon genug). Enthält
Timeout, gzip, höfliche Wiederholversuche und Respekt vor 429/Retry-After.
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from io import BytesIO

from .config import USER_AGENT


class SourceError(RuntimeError):
    """Eine Quelle konnte nicht gelesen werden – der Lauf geht trotzdem weiter."""


def _decode(response) -> bytes:
    raw = response.read()
    if response.headers.get("Content-Encoding") == "gzip":
        with gzip.GzipFile(fileobj=BytesIO(raw)) as unzipped:
            return unzipped.read()
    return raw


def request(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict | None = None,
    timeout: int = 20,
    retries: int = 2,
    backoff: float = 2.0,
) -> bytes:
    """
    Eine URL abrufen und den Rumpf zurückgeben.

    Wiederholt nur bei Fehlern, bei denen ein zweiter Versuch sinnvoll ist
    (Timeout, 5xx, 429). Bei 404 oder kaputtem Feed wird sofort aufgegeben –
    endloses Nachbohren hilft niemandem.
    """
    all_headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
    }
    all_headers.update(headers or {})

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=all_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return _decode(response)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                wait = float(exc.headers.get("Retry-After") or backoff * (attempt + 1))
                time.sleep(min(wait, 30.0))
                continue
            if 500 <= exc.code < 600 and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise SourceError(f"HTTP {exc.code} für {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue

    raise SourceError(f"{url} nicht erreichbar: {last_error}")


def get_json(url: str, *, timeout: int = 20, retries: int = 2, headers: dict | None = None) -> dict:
    payload = {"Accept": "application/json"}
    payload.update(headers or {})
    body = request(url, headers=payload, timeout=timeout, retries=retries)
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError as exc:
        raise SourceError(f"Ungültiges JSON von {url}: {exc}") from exc


def post_json(url: str, payload: dict, *, timeout: int = 20, retries: int = 2) -> dict:
    body = request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=timeout,
        retries=retries,
    )
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError as exc:
        raise SourceError(f"Ungültiges JSON von {url}: {exc}") from exc


def get_text(url: str, *, timeout: int = 20, retries: int = 1) -> str:
    return request(url, timeout=timeout, retries=retries).decode("utf-8", "replace")
