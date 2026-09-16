# -*- coding: utf-8 -*-
"""Gemeinsame Test-Bausteine."""

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker.config import Retention, Settings          # noqa: E402
from tracker.models import extract_type, extract_year    # noqa: E402

#: Feste "Jetzt"-Zeit – Aufbewahrungstests dürfen nicht von der Uhr abhängen.
NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)


def anime(anime_id, title="Titel", info="TV-Serie, 12 (2024)", **extra):
    entry = {
        "id": anime_id,
        "title": title,
        "url": f"https://www.anisearch.de/anime/{anime_id},{title.lower().replace(' ', '-')}",
        "image": f"https://cdn.anisearch.de/{anime_id}.webp",
        "info": info,
        "year": extract_year(info),
        "type": extract_type(info),
    }
    entry.update(extra)
    return entry


@pytest.fixture
def policy():
    return Retention(
        max_age_days=365,
        stale_grace_days=14,
        tombstone_days=90,
        max_entries_per_category=5,
        news_max_age_days=30,
        news_max_items=3,
    )


@pytest.fixture
def settings(tmp_path, policy):
    return Settings(
        data_file=str(tmp_path / "anime_data.json"),
        retention=policy,
        sources=("anisearch",),
    )


@pytest.fixture
def now():
    return NOW
