#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemeinsame Scraping- und Datenlogik für den Anime-Synchro-Tracker.

Dieses Modul ist die *einzige* Stelle, an der anisearch.de ausgelesen und
anime_data.json geschrieben wird. Sowohl der GitHub-Actions-Scraper
(scraper_standalone.py) als auch der lokale Flask-Server
(scrape_anisearch_fixed.py) verwenden es.

Zentrale Garantien:

1. **Kein Anime wird doppelt gespeichert.** Die drei Kategorien
   (kommende / aktuelle / abgeschlossen) sind nach dem Zusammenführen
   garantiert überschneidungsfrei – jeder Anime taucht in genau einer
   Kategorie auf, auch wenn anisearch.de denselben Eintrag in mehreren
   Filter-Abfragen liefert.

2. **Keine unnötigen Schreibvorgänge.** anime_data.json wird nur dann neu
   geschrieben, wenn sich die Anime-Daten tatsächlich geändert haben
   (Vergleich über einen Content-Hash). Ein reiner Zeitstempel-Wechsel
   erzeugt keinen neuen Dateiinhalt und damit auch keinen Commit.

Die reinen Datenfunktionen (dedupe_categories, build_payload, data_hash,
write_if_changed) kommen ohne Netzwerk und ohne Playwright aus und sind in
test_data_pipeline.py abgedeckt.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

# ─── Konstanten ───────────────────────────────────────────────────────────────

BASE_URL = "https://www.anisearch.de"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_MAX_PAGES = 5      # Obergrenze an Listenseiten pro Kategorie
DELAY_MS = 1500            # Wartezeit zwischen Seitenaufrufen (Höflichkeit ggü. anisearch.de)
# Pfade immer relativ zum Projektverzeichnis auflösen, damit der Scraper
# unabhängig vom Arbeitsverzeichnis (Doppelklick, GitHub Actions, cron) immer
# dieselbe Datei schreibt statt versehentlich eine zweite anzulegen.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "anime_data.json")
HTML_FILE = os.path.join(BASE_DIR, "Anime Synchro Tracker v11.0.1.html")
DATA_VERSION = "5.0"

# Reihenfolge = Priorität beim Entdoppeln. Ein Anime, der bereits in einer
# weiter oben stehenden Kategorie steckt, wird aus den folgenden entfernt.
# "Bald verfügbar" ist die interessanteste Information und gewinnt deshalb.
CATEGORY_ORDER = ("kommende", "aktuelle", "abgeschlossen")

CATEGORY_LABELS = {
    "kommende": "Bald verfügbar (geplante Syncros)",
    "aktuelle": "Kürzlich erschienen (laufende Syncros)",
    "abgeschlossen": "Abgeschlossene deutsche Syncros",
}

# Filter-Parameter je Kategorie.
#
# WICHTIG: Sollte anisearch.de seine Filter-Parameter ändern, ist das hier die
# einzige Stelle, die angepasst werden muss. Ob die Filter greifen, prüft der
# Scraper nach jedem Lauf selbst (siehe dedupe_categories) und meldet es als
# Warnung – doppelte Daten landen dadurch nicht mehr in der JSON.
CATEGORY_PARAMS = {
    "kommende":      "char=all&dubbed=de&dubbed_status=3&sort=date&order=asc",
    "aktuelle":      "char=all&dubbed=de&dubbed_status=2&sort=date&order=desc",
    "abgeschlossen": "char=all&dubbed=de&dubbed_status=1&sort=date&order=desc",
}

CATEGORY_MAX_PAGES = {
    "kommende": DEFAULT_MAX_PAGES,
    "aktuelle": DEFAULT_MAX_PAGES,
    "abgeschlossen": 3,   # sehr großer Bestand, bewusst begrenzt
}

ANIME_TYPES = ("TV-Serie", "Film", "OVA", "Web", "TV-Spezial", "Bonus", "Musikvideo")


# ─── Reine Datenlogik (netzwerkfrei, getestet) ────────────────────────────────

def extract_year(info: str) -> int:
    """Jahr aus einem Info-String wie 'TV-Serie, 12 (2024)' lesen."""
    m = re.search(r"\((\d{4})\)", info or "")
    if m:
        return int(m.group(1))
    m = re.search(r"\b((?:19|20)\d{2})\b", info or "")
    return int(m.group(1)) if m else 0


def extract_type(info: str) -> str:
    """Medienformat aus dem Info-String lesen."""
    for t in ANIME_TYPES:
        if t in (info or ""):
            return t
    return "Anime"


def anime_key(anime: dict) -> str:
    """
    Stabiler Schlüssel für die Deduplizierung.

    Normalerweise die anisearch-ID. Fehlt sie (Parser-Ausfall, id == 0), wird
    auf URL bzw. Titel ausgewichen – früher fielen alle Einträge ohne ID auf
    denselben Schlüssel 0 zusammen und wurden dadurch fälschlich verworfen.
    """
    anime_id = anime.get("id") or 0
    if anime_id:
        return f"id:{anime_id}"
    url = (anime.get("url") or "").strip().lower()
    if url:
        return f"url:{url}"
    return f"title:{(anime.get('title') or '').strip().lower()}"


def sort_animes(animes: list) -> list:
    """
    Deterministische Reihenfolge: neueste zuerst, dann alphabetisch.

    Die Anzeige-Sortierung übernimmt ohnehin das Frontend. Eine feste
    Reihenfolge in der Datei sorgt dafür, dass unveränderte Daten auch einen
    unveränderten Dateiinhalt ergeben – sonst erzeugt jede Umsortierung durch
    anisearch.de einen Diff und damit einen überflüssigen Commit.
    """
    return sorted(
        animes,
        key=lambda a: (-(a.get("year") or 0), (a.get("title") or "").lower(), anime_key(a)),
    )


def dedupe_categories(raw: dict) -> tuple:
    """
    Kategorien zusammenführen und entdoppeln.

    Rückgabe: (kategorien, warnungen)

    * Innerhalb einer Kategorie bleibt je Anime nur der erste Treffer.
    * Über Kategorien hinweg gewinnt die Kategorie mit der höheren Priorität
      (CATEGORY_ORDER); in allen weiteren wird der Anime entfernt.
    * Liefern zwei Filter-Abfragen (nahezu) dieselbe Menge, ist das ein Zeichen
      dafür, dass anisearch.de den Filter ignoriert hat. Das wird als Warnung
      gemeldet, statt die Daten doppelt zu speichern.
    """
    categories: dict = {}
    warnings: list = []
    seen: dict = {}          # key -> Kategorie, die den Anime bekommen hat
    raw_keys: dict = {}      # Kategorie -> Schlüsselmenge vor dem Entdoppeln

    for name in CATEGORY_ORDER:
        entries = raw.get(name) or []
        unique: list = []
        local_seen: set = set()
        dropped_internal = 0
        dropped_cross: dict = {}

        for anime in entries:
            if not (anime.get("title") or "").strip():
                continue
            key = anime_key(anime)

            if key in local_seen:
                dropped_internal += 1
                continue
            local_seen.add(key)

            owner = seen.get(key)
            if owner is not None:
                dropped_cross[owner] = dropped_cross.get(owner, 0) + 1
                continue

            seen[key] = name
            entry = dict(anime)
            entry["status"] = name
            unique.append(entry)

        raw_keys[name] = local_seen
        categories[name] = sort_animes(unique)

        if dropped_internal:
            warnings.append(
                f"{name}: {dropped_internal} Duplikat(e) innerhalb der Kategorie entfernt"
            )
        for owner, count in dropped_cross.items():
            warnings.append(
                f"{name}: {count} Eintrag/Einträge entfernt, die bereits in '{owner}' stehen"
            )

    # Filter-Plausibilität: identische Ergebnismengen deuten auf einen von
    # anisearch.de ignorierten Filter hin.
    names = list(CATEGORY_ORDER)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            a, b = raw_keys.get(first, set()), raw_keys.get(second, set())
            if not a or not b:
                continue
            overlap = len(a & b) / min(len(a), len(b))
            if overlap >= 0.9:
                warnings.append(
                    f"Filter greift nicht: '{first}' und '{second}' liefern zu "
                    f"{overlap:.0%} dieselben Anime – bitte CATEGORY_PARAMS in "
                    f"anisearch_scraper.py gegen anisearch.de prüfen"
                )

    return categories, warnings


def data_hash(categories: dict) -> str:
    """Content-Hash über die reinen Anime-Daten (ohne Zeitstempel/Metadaten)."""
    payload = {
        name: [
            {k: v for k, v in anime.items() if k != "status"}
            for anime in categories.get(name, [])
        ]
        for name in CATEGORY_ORDER
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_payload(categories: dict, warnings=None, previous=None) -> dict:
    """
    Fertige JSON-Struktur bauen.

    Die Schlüssel kommende/aktuelle/abgeschlossen/timestamp bleiben erhalten,
    damit meine-anime-welt.de und der bestehende Tracker ohne Änderung
    weiterlaufen. Neu sind nur zusätzliche Metadaten.
    """
    warnings = list(warnings or [])
    digest = data_hash(categories)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    # Zeitpunkt der letzten *inhaltlichen* Änderung fortschreiben.
    changed_at = now
    if previous and previous.get("data_hash") == digest:
        changed_at = previous.get("data_changed_at") or previous.get("timestamp") or now

    counts = {name: len(categories.get(name, [])) for name in CATEGORY_ORDER}
    payload = {name: categories.get(name, []) for name in CATEGORY_ORDER}
    payload.update({
        "timestamp": changed_at,          # Rückwärtskompatibel: letzter Datenstand
        "data_changed_at": changed_at,
        "data_hash": digest,
        "counts": counts,
        "total": sum(counts.values()),
        "source": "anisearch.de",
        "version": DATA_VERSION,
        "scraping": False,
        "warnings": warnings,
    })
    return payload


def load_existing(path: str = DATA_FILE) -> dict:
    """Vorhandene anime_data.json laden (leeres dict, wenn nicht lesbar)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_if_changed(categories: dict, warnings=None, path: str = DATA_FILE) -> tuple:
    """
    JSON nur schreiben, wenn sich die Anime-Daten geändert haben.

    Rückgabe: (geschrieben: bool, payload: dict)

    Dadurch entsteht kein täglicher Commit mehr, nur weil sich der Zeitstempel
    verschoben hat – die Datei bleibt bei gleichen Daten Byte für Byte gleich.
    """
    previous = load_existing(path)
    payload = build_payload(categories, warnings=warnings, previous=previous)

    if previous.get("data_hash") == payload["data_hash"] and previous.get("warnings", []) == payload["warnings"]:
        return False, payload

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, path)   # atomar: nie eine halb geschriebene Datei ausliefern
    return True, payload


# ─── Scraping (Playwright) ────────────────────────────────────────────────────

def category_url(name: str, page_num: int = 1) -> str:
    return f"{BASE_URL}/anime/index/page-{page_num}?{CATEGORY_PARAMS[name]}"


def accept_cookies(page) -> bool:
    """Cookie-Banner wegklicken. True, wenn tatsächlich geklickt wurde."""
    for selector in ("text=ALLES AKZEPTIEREN", "text=Alles akzeptieren", "button:has-text('akzeptieren')"):
        try:
            consent = page.locator(selector)
            if consent.count() > 0:
                consent.first.click(timeout=5000)
                page.wait_for_timeout(1500)
                print("   ✅ Cookie-Banner akzeptiert")
                return True
        except Exception:
            continue
    return False


def parse_anime_list(page) -> list:
    """Anime-Einträge der aktuell geladenen Listenseite auslesen."""
    results = []
    try:
        page.wait_for_selector(".covers", timeout=10000)
    except Exception:
        print("   ⚠️  Liste (.covers) nicht gefunden")
        return results

    for item in page.locator("ul.covers li a.anime-item").all():
        try:
            href = item.get_attribute("href") or ""
            title_el = item.locator("span.title")
            title = title_el.inner_text().strip() if title_el.count() > 0 else ""
            if not title:
                continue

            date_el = item.locator("span.date")
            info = date_el.inner_text().strip() if date_el.count() > 0 else ""
            img_el = item.locator("img")
            image = (img_el.get_attribute("src") or "") if img_el.count() > 0 else ""

            anime_id = 0
            m = re.search(r"(\d+),", href.split("/")[-1])
            if m:
                anime_id = int(m.group(1))

            results.append({
                "id": anime_id,
                "title": title,
                "url": f"{BASE_URL}/{href.lstrip('/')}",
                "image": image,
                "info": info,
                "year": extract_year(info),
                "type": extract_type(info),
            })
        except Exception:
            continue
    return results


def scrape_category(page, name: str, max_pages: int = None) -> list:
    """
    Eine Kategorie über alle erreichbaren Listenseiten einlesen.

    Die Paginierung stoppt, sobald eine Seite keine neuen Anime mehr liefert.
    Damit läuft der Scraper auch dann korrekt, wenn anisearch.de die
    Seitenanzahl nicht mehr im erwarteten Format ausgibt (früher wurde in dem
    Fall stillschweigend nur Seite 1 gelesen).
    """
    max_pages = max_pages or CATEGORY_MAX_PAGES.get(name, DEFAULT_MAX_PAGES)
    label = CATEGORY_LABELS.get(name, name)
    print(f"\n{'=' * 60}\n🔍 {label}\n{'=' * 60}")

    results: list = []
    seen: set = set()

    for page_num in range(1, max_pages + 1):
        url = category_url(name, page_num)
        print(f"📄 Seite {page_num}: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(DELAY_MS)
        except Exception as e:
            print(f"   ⚠️  Seite {page_num} nicht ladbar: {e}")
            break

        if page_num == 1:
            # Der Consent-Dialog kann die Filter-Parameter verschlucken –
            # deshalb nach dem Akzeptieren die gefilterte URL erneut aufrufen.
            if accept_cookies(page):
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(DELAY_MS)

            landed = page.url or ""
            if "dubbed_status" in CATEGORY_PARAMS[name] and "dubbed_status" not in landed:
                print(f"   ⚠️  Filter-Parameter nicht in der Ziel-URL: {landed}")

        new_entries = [a for a in parse_anime_list(page) if anime_key(a) not in seen]
        for a in new_entries:
            seen.add(anime_key(a))
        results.extend(new_entries)
        print(f"   ✅ {len(new_entries)} neue Anime (Kategorie gesamt: {len(results)})")

        if not new_entries:
            print("   ↩️  Keine neuen Einträge – Paginierung beendet")
            break

    print(f"✅ {label}: {len(results)} Anime")
    return results


def scrape_all(playwright, categories=None) -> dict:
    """Alle Kategorien in einem Browser-Kontext einlesen."""
    categories = categories or list(CATEGORY_ORDER)
    browser = playwright.chromium.launch(headless=True)
    try:
        context = browser.new_context(user_agent=USER_AGENT, locale="de-DE")
        page = context.new_page()
        return {name: scrape_category(page, name) for name in categories}
    finally:
        browser.close()


def scrape_and_store(path: str = DATA_FILE) -> tuple:
    """
    Kompletter Durchlauf: scrapen → entdoppeln → nur bei Änderung speichern.

    Rückgabe: (geschrieben: bool, payload: dict, warnungen: list)
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        raw = scrape_all(pw)

    categories, warnings = dedupe_categories(raw)
    written, payload = write_if_changed(categories, warnings=warnings, path=path)
    return written, payload, warnings


def print_summary(payload: dict, written: bool, path: str = DATA_FILE) -> None:
    counts = payload.get("counts", {})
    print(f"\n{'=' * 60}")
    print(f"📊 GESAMT: {payload.get('total', 0)} Anime (jeder genau einmal)")
    print(f"   {counts.get('kommende', 0)} geplant | "
          f"{counts.get('aktuelle', 0)} aktuell | "
          f"{counts.get('abgeschlossen', 0)} abgeschlossen")
    print(f"{'=' * 60}")

    for warning in payload.get("warnings", []):
        print(f"⚠️  {warning}")

    if written:
        print(f"\n💾 {path} aktualisiert (Stand: {payload.get('data_changed_at')})")
    else:
        print(f"\n✅ Keine Datenänderung – {path} bleibt unverändert (kein Commit nötig)")
