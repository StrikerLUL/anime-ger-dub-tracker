#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kompatibilitäts-Modul (veraltet).

Die Logik liegt seit Version 6.0 im Paket `tracker`. Dieses Modul gibt es nur
noch, damit ältere Skripte und Lesezeichen weiterlaufen:

    # alt
    from anisearch_scraper import dedupe_categories, write_if_changed
    # neu
    from tracker.merge import dedupe_categories
    from tracker.store import write_if_changed
"""

from tracker.config import (          # noqa: F401
    BASE_DIR,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    DATA_FILE,
    DATA_VERSION,
    HTML_FILE,
)
from tracker.merge import dedupe_categories          # noqa: F401
from tracker.models import (                          # noqa: F401
    ANIME_TYPES,
    anime_key,
    extract_type,
    extract_year,
    sort_animes,
)
from tracker.sources.anisearch import (               # noqa: F401
    BASE_URL,
    CATEGORY_PARAMS,
    category_url,
    parse_anime_list,
)
from tracker.store import build_payload, data_hash, load as load_existing  # noqa: F401

__all__ = [
    "ANIME_TYPES", "BASE_DIR", "BASE_URL", "CATEGORY_LABELS", "CATEGORY_ORDER",
    "CATEGORY_PARAMS", "DATA_FILE", "DATA_VERSION", "HTML_FILE", "anime_key",
    "build_payload", "category_url", "data_hash", "dedupe_categories",
    "extract_type", "extract_year", "load_existing", "parse_anime_list",
    "sort_animes",
]
