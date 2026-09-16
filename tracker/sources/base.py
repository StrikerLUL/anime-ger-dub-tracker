#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemeinsames Gerüst für alle Datenquellen.

Grundregel: **eine kaputte Quelle darf den Lauf nicht kippen.** anisearch.de
liefert die Kategorien, alles andere reichert nur an. Fällt AniList aus, sind
eben ein paar Genres weniger drin – die Website bekommt trotzdem ihre Daten.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SourceReport:
    """Was eine Quelle in diesem Lauf geliefert hat (fürs Log, nicht für die JSON)."""

    name: str
    ok: bool = True
    items: int = 0
    error: str = ""
    warnings: list = field(default_factory=list)
    seconds: float = 0.0

    def line(self) -> str:
        if not self.ok:
            return f"❌ {self.name}: {self.error}"
        return f"✅ {self.name}: {self.items} Treffer ({self.seconds:.1f}s)"


def run_source(name: str, func, *args, **kwargs):
    """
    Eine Quelle ausführen und Fehler in einen Report verwandeln.

    Rückgabe: (ergebnis_oder_None, SourceReport)
    """
    started = time.monotonic()
    try:
        result = func(*args, **kwargs)
    except Exception as exc:                       # noqa: BLE001 – bewusst breit
        return None, SourceReport(
            name=name, ok=False, error=f"{type(exc).__name__}: {exc}",
            seconds=time.monotonic() - started,
        )

    items = 0
    if isinstance(result, dict):
        items = sum(len(v) if isinstance(v, (list, tuple)) else 1 for v in result.values())
    elif isinstance(result, (list, tuple)):
        items = len(result)

    return result, SourceReport(
        name=name, ok=True, items=items, seconds=time.monotonic() - started,
    )
