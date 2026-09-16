#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quelle 1: anisearch.de – die einzige Quelle, die weiß, welche Anime eine
**deutsche Synchronisation** bekommen. Sie liefert deshalb die Kategorien,
alle anderen Quellen reichern nur an.

Gelesen wird mit Playwright (die Liste wird per JavaScript aufgebaut).
"""

from __future__ import annotations

import re

from ..config import (
    BROWSER_USER_AGENT,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    Settings,
)
from ..models import anime_key, extract_episodes, extract_type, extract_year

BASE_URL = "https://www.anisearch.de"

# Filter-Parameter je Kategorie.
#
# WICHTIG: Sollte anisearch.de seine Filter ändern, ist das hier die einzige
# Stelle, die angepasst werden muss. Ob die Filter überhaupt greifen, prüft die
# Pipeline nach jedem Lauf selbst (siehe merge.dedupe_categories) – doppelte
# Daten landen dadurch nicht in der JSON.
CATEGORY_PARAMS = {
    "kommende":      "char=all&dubbed=de&dubbed_status=3&sort=date&order=asc",
    "aktuelle":      "char=all&dubbed=de&dubbed_status=2&sort=date&order=desc",
    "abgeschlossen": "char=all&dubbed=de&dubbed_status=1&sort=date&order=desc",
}

COOKIE_SELECTORS = (
    "text=ALLES AKZEPTIEREN",
    "text=Alles akzeptieren",
    "button:has-text('akzeptieren')",
    "button:has-text('Accept')",
)


def category_url(name: str, page_num: int = 1) -> str:
    return f"{BASE_URL}/anime/index/page-{page_num}?{CATEGORY_PARAMS[name]}"


def max_pages_for(name: str, settings: Settings) -> int:
    # "abgeschlossen" hat einen sehr großen Bestand – bewusst begrenzt.
    return settings.max_pages_done if name == "abgeschlossen" else settings.max_pages


def accept_cookies(page) -> bool:
    """Cookie-Banner wegklicken. True, wenn tatsächlich geklickt wurde."""
    for selector in COOKIE_SELECTORS:
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
        page.wait_for_selector(".covers", timeout=15000)
    except Exception:
        print("   ⚠️  Liste (.covers) nicht gefunden – Layout geändert?")
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
            image = ""
            if img_el.count() > 0:
                image = (
                    img_el.first.get_attribute("src")
                    or img_el.first.get_attribute("data-src")
                    or ""
                )

            anime_id = 0
            match = re.search(r"(\d+),", href.split("/")[-1])
            if match:
                anime_id = int(match.group(1))

            episodes = extract_episodes(info)
            entry = {
                "id": anime_id,
                "title": title,
                "url": f"{BASE_URL}/{href.lstrip('/')}",
                "image": image,
                "info": info,
                "year": extract_year(info),
                "type": extract_type(info),
            }
            if episodes:
                entry["episodes"] = episodes
            results.append(entry)
        except Exception:
            continue
    return results


def scrape_category(page, name: str, settings: Settings) -> list:
    """
    Eine Kategorie über alle erreichbaren Listenseiten einlesen.

    Die Paginierung stoppt, sobald eine Seite keine neuen Anime mehr liefert.
    Damit läuft der Scraper auch dann korrekt, wenn anisearch.de die
    Seitenanzahl nicht mehr im erwarteten Format ausgibt.
    """
    max_pages = max_pages_for(name, settings)
    label = CATEGORY_LABELS.get(name, name)
    print(f"\n{'=' * 60}\n🔍 {label}\n{'=' * 60}")

    results: list = []
    seen: set = set()

    for page_num in range(1, max_pages + 1):
        url = category_url(name, page_num)
        print(f"📄 Seite {page_num}: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(settings.page_delay_ms)
        except Exception as exc:
            print(f"   ⚠️  Seite {page_num} nicht ladbar: {exc}")
            break

        if page_num == 1:
            # Der Consent-Dialog kann die Filter-Parameter verschlucken –
            # deshalb nach dem Akzeptieren die gefilterte URL erneut aufrufen.
            if accept_cookies(page):
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(settings.page_delay_ms)

            landed = page.url or ""
            if "dubbed_status" in CATEGORY_PARAMS[name] and "dubbed_status" not in landed:
                print(f"   ⚠️  Filter-Parameter nicht in der Ziel-URL: {landed}")

        new_entries = [a for a in parse_anime_list(page) if anime_key(a) not in seen]
        for entry in new_entries:
            seen.add(anime_key(entry))
        results.extend(new_entries)
        print(f"   ✅ {len(new_entries)} neue Anime (Kategorie gesamt: {len(results)})")

        if not new_entries:
            print("   ↩️  Keine neuen Einträge – Paginierung beendet")
            break

    print(f"✅ {label}: {len(results)} Anime")
    return results


def scrape(settings: Settings, categories=None) -> dict:
    """Alle Kategorien in einem Browser-Kontext einlesen."""
    from playwright.sync_api import sync_playwright

    names = list(categories or CATEGORY_ORDER)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=BROWSER_USER_AGENT, locale="de-DE")
            page = context.new_page()
            # Bilder/Fonts sparen wir uns – wir brauchen nur das Markup.
            page.route(
                re.compile(r"\.(png|jpe?g|webp|gif|woff2?|ttf|svg)(\?.*)?$"),
                lambda route: route.abort(),
            )
            return {name: scrape_category(page, name, settings) for name in names}
        finally:
            browser.close()
