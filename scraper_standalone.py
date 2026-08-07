#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anisearch.de Standalone Scraper für GitHub Actions
Kein Flask, kein Server – erzeugt nur anime_data.json

Wird automatisch täglich durch GitHub Actions ausgeführt.
"""

import json
import sys
import os
import re
from datetime import datetime

BASE_URL = "https://www.anisearch.de"
HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_PAGES = 5   # Max Seiten pro Kategorie
DELAY_MS  = 1500


def accept_cookies(page):
    try:
        consent = page.locator('text=ALLES AKZEPTIEREN')
        if consent.count() > 0:
            consent.first.click()
            page.wait_for_timeout(1500)
            print("✅ Cookie-Banner akzeptiert")
    except Exception:
        pass


def extract_year(date_str: str) -> int:
    m = re.search(r'\((\d{4})\)', date_str)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(20\d{2})\b', date_str)
    if m:
        return int(m.group(1))
    return 0


def extract_type(date_str: str) -> str:
    types = ['TV-Serie', 'Film', 'OVA', 'Web', 'TV-Spezial', 'Bonus', 'Musikvideo']
    for t in types:
        if t in date_str:
            return t
    return 'Anime'


def parse_anime_list(page) -> list:
    results = []
    try:
        page.wait_for_selector('.covers', timeout=10000)
    except Exception:
        print("   ⚠️  .covers Selektor nicht gefunden")
        return results

    items = page.locator('ul.covers li a.anime-item').all()
    for item in items:
        try:
            href     = item.get_attribute('href') or ''
            title_el = item.locator('span.title')
            title    = title_el.inner_text().strip() if title_el.count() > 0 else ''
            date_el  = item.locator('span.date')
            date_str = date_el.inner_text().strip() if date_el.count() > 0 else ''
            img_el   = item.locator('img')
            img      = img_el.get_attribute('src') or '' if img_el.count() > 0 else ''

            anime_id = 0
            if '/' in href:
                part = href.split('/')[-1]
                if ',' in part:
                    try:
                        anime_id = int(part.split(',')[0])
                    except Exception:
                        pass

            if title:
                results.append({
                    'id':    anime_id,
                    'title': title,
                    'url':   f"{BASE_URL}/{href}",
                    'image': img,
                    'info':  date_str,
                    'year':  extract_year(date_str),
                    'type':  extract_type(date_str),
                })
        except Exception:
            continue
    return results


def goto_with_retry(page, url: str, max_attempts: int = 3) -> bool:
    for attempt in range(1, max_attempts + 1):
        timeout_ms = 30000 + ((attempt - 1) * 15000)
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            return True
        except Exception as e:
            print(f"   ⚠️  Laden fehlgeschlagen ({attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                wait_s = attempt * 2
                print(f"   ⏳ Neuer Versuch in {wait_s}s...")
                page.wait_for_timeout(wait_s * 1000)
    return False


def scrape_category(pw, url_params: str, label: str, max_pages: int = MAX_PAGES) -> list:
    all_results: list = []
    print(f"\n{'='*55}")
    print(f"🔍 {label}")
    print(f"{'='*55}")

    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=HEADERS['User-Agent'],
        locale='de-DE'
    )
    page = context.new_page()

    try:
        url = f"{BASE_URL}/anime/index/page-1?{url_params}"
        print(f"📄 Lade Seite 1: {url}")
        if not goto_with_retry(page, url):
            print("   ❌ Seite 1 konnte nicht geladen werden")
            return []
        page.wait_for_timeout(DELAY_MS)
        accept_cookies(page)
        page.wait_for_timeout(DELAY_MS)

        # Gesamt-Seitenanzahl
        total_pages = 1
        try:
            nav_info = page.locator('.pagenav-info').inner_text(timeout=3000)
            m = re.search(r'von (\d+)', nav_info)
            if m:
                total_pages = min(int(m.group(1)), max_pages)
        except Exception:
            pass
        print(f"   → {total_pages} Seite(n) gefunden")

        results = parse_anime_list(page)
        all_results.extend(results)
        print(f"   ✅ Seite 1: {len(results)} Anime")

        for p_num in range(2, total_pages + 1):
            url = f"{BASE_URL}/anime/index/page-{p_num}?{url_params}"
            print(f"📄 Lade Seite {p_num}...")
            if not goto_with_retry(page, url):
                print(f"   ⚠️  Überspringe Seite {p_num} nach mehreren Fehlversuchen")
                break
            page.wait_for_timeout(DELAY_MS)
            results = parse_anime_list(page)
            all_results.extend(results)
            print(f"   ✅ Seite {p_num}: {len(results)} Anime")

    finally:
        browser.close()

    # Duplikate entfernen
    seen = set()
    unique = []
    for a in all_results:
        if a['id'] not in seen:
            seen.add(a['id'])
            unique.append(a)

    print(f"\n✅ {label}: {len(unique)} Anime gesamt")
    return unique


def main():
    print("=" * 55)
    print("🎬 ANISEARCH STANDALONE SCRAPER für GitHub Actions")
    print("=" * 55)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        # Geplante Dubs (Status 3)
        kommende = scrape_category(
            pw,
            url_params='char=all&dubbed=de&dubbed_status=3&sort=date&order=asc',
            label='Bald verfügbar (Geplante Syncros)'
        )

        # Laufende Dubs (Status 2)
        aktuelle = scrape_category(
            pw,
            url_params='char=all&dubbed=de&dubbed_status=2&sort=date&order=desc',
            label='Kürzlich erschienen (Laufende Syncros)'
        )

        # Abgeschlossene Dubs (Status 1) – nur 3 Seiten
        abgeschlossen = scrape_category(
            pw,
            url_params='char=all&dubbed=de&dubbed_status=1&sort=date&order=desc',
            label='Abgeschlossene Deutsche Syncros',
            max_pages=3
        )

    total = len(kommende) + len(aktuelle) + len(abgeschlossen)
    print(f"\n{'='*55}")
    print(f"📊 GESAMT: {total} Anime")
    print(f"   {len(kommende)} geplant | {len(aktuelle)} aktuell | {len(abgeschlossen)} abgeschlossen")
    print(f"{'='*55}")

    # JSON speichern
    data = {
        'kommende':      kommende,
        'aktuelle':      aktuelle,
        'abgeschlossen': abgeschlossen,
        'timestamp':     datetime.utcnow().isoformat() + 'Z',
        'source':        'anisearch.de',
        'version':       '4.0',
        'scraping':      False
    }

    output_path = os.path.join(os.path.dirname(__file__), 'anime_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Gespeichert: anime_data.json ({total} Anime)")

    if total == 0:
        print("\n❌ FEHLER: Keine Daten gefunden – Scraper hat nichts geladen!")
        sys.exit(1)

    print("\n✅ Fertig! GitHub Actions kann jetzt die Datei committen.")


if __name__ == '__main__':
    main()
