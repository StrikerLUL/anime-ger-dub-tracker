#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aufbewahrung: Daten dürfen nicht ewig in anime_data.json liegen bleiben.

Vier Regeln, alle über Umgebungsvariablen einstellbar (siehe config.Retention):

1. **Verschwunden = gelöscht.** Liefert keine Quelle einen Anime mehr, bekommt
   er ein `missing_since`. Nach `stale_grace_days` (Standard 14) fliegt er raus.
   Die Karenz sorgt dafür, dass ein einzelner Fehllauf nicht die halbe Datei
   leert.

2. **Höchstalter.** Jeder Eintrag hat ein `expires_at` = erstes Auftauchen +
   `max_age_days` (Standard 365). Danach wird er entfernt – auch wenn die
   Quelle ihn noch führt.

3. **Rückkehrsperre.** Ein wegen Höchstalter entfernter Anime landet für
   `tombstone_days` (Standard 90) auf einer Sperrliste. Sonst stünde er am
   nächsten Tag wieder in der Datei und würde jeden Tag einen Commit erzeugen.

4. **Obergrenze je Kategorie.** Mehr als `max_entries_per_category` Einträge
   (Standard 400) werden nicht gespeichert; die ältesten fallen weg. Damit
   bleibt die Datei auch dann klein, wenn eine Quelle plötzlich Tausende
   Einträge liefert.

Alle Funktionen sind netzwerkfrei und deterministisch (die Zeit kommt als
Parameter herein), deshalb vollständig testbar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .config import CATEGORY_ORDER, Retention
from .models import anime_key, days_between, iso, parse_iso, plus_days, sort_animes


@dataclass
class RetentionStats:
    """Was dieser Lauf mit den Daten gemacht hat (fürs Log, nicht für die Datei)."""

    added: int = 0
    kept: int = 0
    missing: int = 0
    returned: int = 0
    removed_stale: int = 0
    removed_expired: int = 0
    removed_capped: int = 0
    tombstones_active: int = 0
    tombstones_expired: int = 0
    skipped_blocked: int = 0
    notes: list = field(default_factory=list)

    @property
    def removed(self) -> int:
        return self.removed_stale + self.removed_expired + self.removed_capped

    def lines(self) -> list:
        out = [
            f"➕ {self.added} neu · ♻️ {self.kept} unverändert · "
            f"🕓 {self.missing} vermisst · ↩️ {self.returned} zurück"
        ]
        if self.removed:
            out.append(
                f"🗑️  {self.removed} gelöscht "
                f"({self.removed_stale}× verschwunden, "
                f"{self.removed_expired}× Höchstalter, "
                f"{self.removed_capped}× über Obergrenze)"
            )
        else:
            out.append("🗑️  nichts zu löschen")
        if self.skipped_blocked:
            out.append(f"⛔ {self.skipped_blocked} Eintrag/Einträge sind noch gesperrt (Rückkehrsperre)")
        out.extend(self.notes)
        return out


def _previous_index(previous: dict) -> dict:
    """Alle Einträge der vorherigen Datei nach Schlüssel indizieren."""
    index = {}
    for name in CATEGORY_ORDER:
        for entry in previous.get(name) or []:
            if isinstance(entry, dict):
                index.setdefault(anime_key(entry), (name, entry))
    return index


def clean_tombstones(retired: dict, now: datetime, policy: Retention) -> tuple:
    """Abgelaufene Sperren entfernen und die Liste begrenzen."""
    active, expired = {}, 0
    for key, until in (retired or {}).items():
        moment = parse_iso(until)
        if moment and moment > now:
            active[key] = iso(moment)
        else:
            expired += 1

    if len(active) > policy.max_tombstones:
        # Die am längsten laufenden Sperren zuerst behalten wäre unfair – wir
        # behalten die, die am ehesten noch relevant sind (kürzeste Restzeit).
        ordered = sorted(active.items(), key=lambda kv: kv[1])
        active = dict(ordered[-policy.max_tombstones:])

    return active, expired


def apply(
    fresh: dict,
    previous: dict,
    *,
    now: datetime,
    policy: Retention,
    sources_ok: bool = True,
) -> tuple:
    """
    Frische Daten mit dem Bestand zusammenführen und die Aufbewahrung anwenden.

    Rückgabe: (kategorien, sperrliste, stats)

    `sources_ok=False` bedeutet: der Scraper hat diesmal nichts (oder
    auffällig wenig) geliefert. Dann wird **nichts** als vermisst markiert –
    ein Netzwerkausfall darf die Website nicht leerräumen. Höchstalter und
    Obergrenzen greifen trotzdem.
    """
    stats = RetentionStats()
    retired, stats.tombstones_expired = clean_tombstones(previous.get("retired") or {}, now, policy)

    previous_entries = _previous_index(previous)
    fresh_keys = {
        anime_key(entry)
        for name in CATEGORY_ORDER
        for entry in (fresh.get(name) or [])
    }

    merged: dict = {name: [] for name in CATEGORY_ORDER}

    # ── 1. Frische Einträge übernehmen ────────────────────────────────────────
    for name in CATEGORY_ORDER:
        for entry in fresh.get(name) or []:
            key = anime_key(entry)
            known = previous_entries.get(key)

            if known is None and key in retired:
                # Rückkehrsperre: erst nach Ablauf wieder aufnehmen.
                stats.skipped_blocked += 1
                continue

            merged_entry = dict(entry)
            merged_entry["status"] = name

            if known is None:
                merged_entry["first_seen"] = iso(now)
                stats.added += 1
            else:
                old = known[1]
                merged_entry["first_seen"] = old.get("first_seen") or iso(now)
                # Angereicherte Felder aus dem Bestand übernehmen, damit die
                # Metadaten nicht bei jedem Lauf neu geholt werden müssen.
                for field_name in ("genres", "studios", "score", "season", "external", "cover"):
                    if field_name not in merged_entry and field_name in old:
                        merged_entry[field_name] = old[field_name]
                if not merged_entry.get("episodes") and old.get("episodes"):
                    merged_entry["episodes"] = old["episodes"]
                if old.get("missing_since"):
                    stats.returned += 1
                else:
                    stats.kept += 1

            merged_entry.pop("missing_since", None)
            merged[name].append(merged_entry)

    # ── 2. Einträge, die keine Quelle mehr liefert ────────────────────────────
    for key, (name, old) in previous_entries.items():
        if key in fresh_keys:
            continue

        entry = dict(old)
        entry.setdefault("first_seen", iso(now))

        if not sources_ok:
            # Quelle war gestört – Bestand unangetastet weiterführen.
            merged.setdefault(name, []).append(entry)
            stats.kept += 1
            continue

        missing_since = parse_iso(entry.get("missing_since")) or now
        if days_between(now, missing_since) >= policy.stale_grace_days:
            stats.removed_stale += 1
            continue

        entry["missing_since"] = iso(missing_since)
        stats.missing += 1
        merged.setdefault(name, []).append(entry)

    # ── 3. Höchstalter ────────────────────────────────────────────────────────
    for name in CATEGORY_ORDER:
        surviving = []
        for entry in merged.get(name, []):
            first_seen = parse_iso(entry.get("first_seen")) or now
            expires_at = plus_days(first_seen, policy.max_age_days)
            if now >= expires_at:
                stats.removed_expired += 1
                retired[anime_key(entry)] = iso(plus_days(now, policy.tombstone_days))
                continue
            entry["expires_at"] = iso(expires_at)
            surviving.append(entry)
        merged[name] = surviving

    # ── 4. Obergrenze je Kategorie ────────────────────────────────────────────
    for name in CATEGORY_ORDER:
        entries = sort_animes(merged.get(name, []))
        if len(entries) > policy.max_entries_per_category:
            stats.removed_capped += len(entries) - policy.max_entries_per_category
            entries = entries[:policy.max_entries_per_category]
        merged[name] = entries

    retired, extra_expired = clean_tombstones(retired, now, policy)
    stats.tombstones_expired += extra_expired
    stats.tombstones_active = len(retired)
    return merged, retired, stats


def prune_news(news: list, *, now: datetime, policy: Retention) -> list:
    """News sind Tagesgeschäft: alt raus, Menge begrenzt."""
    fresh = []
    for item in news or []:
        published = parse_iso(item.get("published"))
        if published and days_between(now, published) > policy.news_max_age_days:
            continue
        fresh.append(item)
    fresh.sort(key=lambda e: (e.get("published") or "", e.get("title", "")), reverse=True)
    return fresh[:policy.news_max_items]
