# -*- coding: utf-8 -*-
"""
Frontend-Tests mit einem echten Browser.

Ausgeliefert wird über einen kleinen HTTP-Server, damit `fetch` auf
anime_data.json funktioniert (aus `file://` heraus blockt Chromium das).

    python -m pytest tests/test_frontend.py -m ui

Ohne Playwright/Chromium werden die Tests übersprungen.
"""

import functools
import http.server
import json
import os
import shutil
import threading
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.ui

sync_playwright = pytest.importorskip(
    "playwright.sync_api", reason="Playwright nicht installiert"
).sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def sample_payload():
    def anime(anime_id, title, year, category, **extra):
        entry = {
            "id": anime_id,
            "title": title,
            "url": f"https://www.anisearch.de/anime/{anime_id}",
            "image": "",
            "info": f"TV-Serie, 12 ({year})",
            "year": year,
            "type": "TV-Serie",
            "status": category,
            "first_seen": iso(NOW - timedelta(days=2)),
            "expires_at": iso(NOW + timedelta(days=363)),
        }
        entry.update(extra)
        return entry

    return {
        "kommende": [anime(1, "Alpha Chronik", 2026, "kommende", genres=["Action", "Drama"])],
        "aktuelle": [
            anime(2, "Beta Legende", 2025, "aktuelle", genres=["Comedy"], studios=["Studio Zwei"], score=82),
            anime(3, "Gamma Reise", 2024, "aktuelle", genres=["Action"]),
        ],
        "abgeschlossen": [anime(4, "Delta Finale", 2019, "abgeschlossen")],
        "news": [{
            "title": "Deutsche Synchro angekündigt",
            "url": "https://example.de/news/1",
            "source": "example.de",
            "published": iso(NOW - timedelta(days=1)),
            "summary": "Die Synchro startet im Herbst.",
        }],
        "timestamp": iso(NOW),
        "data_changed_at": iso(NOW),
        "data_hash": "testhash",
        "counts": {"kommende": 1, "aktuelle": 2, "abgeschlossen": 1, "news": 1},
        "total": 4,
        "source": "anisearch.de",
        "sources": ["anisearch", "anilist"],
        "version": "6.0",
        "retention": {"max_age_days": 365, "stale_grace_days": 14},
        "scraping": False,
        "warnings": [],
    }


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """index.html samt Testdaten über einen lokalen HTTP-Server ausliefern."""
    directory = tmp_path_factory.mktemp("site")
    shutil.copy(os.path.join(ROOT, "index.html"), directory / "index.html")
    (directory / "anime_data.json").write_text(
        json.dumps(sample_payload(), ensure_ascii=False), encoding="utf-8"
    )

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()


@pytest.fixture(scope="module")
def browser():
    # In Umgebungen mit vorinstalliertem Chromium kann der Pfad über
    # PLAYWRIGHT_CHROMIUM_EXECUTABLE gesetzt werden; sonst nimmt Playwright
    # seinen eigenen Browser.
    options = {}
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if executable:
        options["executable_path"] = executable

    try:
        with sync_playwright() as playwright:
            instance = playwright.chromium.launch(**options)
            try:
                yield instance
            finally:
                instance.close()
    except Exception as exc:                        # noqa: BLE001
        pytest.skip(f"Chromium nicht startbar: {exc}")


@pytest.fixture
def page(browser, site):
    context = browser.new_context(locale="de-DE")
    page = context.new_page()
    page.goto(site)
    page.wait_for_selector(".anime-card", timeout=15000)
    try:
        yield page
    finally:
        context.close()


# ─── Daten & Anzeige ──────────────────────────────────────────────────────────

def test_alle_anime_werden_angezeigt(page):
    assert page.locator(".anime-card").count() == 4


def test_kein_anime_wird_doppelt_gerendert(page):
    ids = page.eval_on_selector_all(".anime-card", "nodes => nodes.map(n => n.dataset.id)")
    assert len(ids) == len(set(ids))


def test_statistik_zeigt_die_gesamtzahl(page):
    assert page.locator(".stat-card").first.locator(".stat-value").inner_text() == "4"


def test_datenstand_wird_angezeigt(page):
    assert "Datenstand" in page.locator("#metaUpdated").inner_text()


def test_aufbewahrung_wird_angezeigt(page):
    assert "365" in page.locator("#metaRetention").inner_text()


def test_news_werden_angezeigt(page):
    assert page.locator("#newsSection").is_visible()
    assert "Deutsche Synchro angekündigt" in page.locator("#newsGrid").inner_text()


def test_karte_hat_tooltip_mit_episoden(page):
    title = page.locator(".anime-card").first.get_attribute("title")
    assert "|" in title and "Episoden" in title


def test_abgeschlossen_tab_erscheint_nur_mit_daten(page):
    assert page.locator("#tabAbgeschlossen").is_visible()


# ─── Filter ───────────────────────────────────────────────────────────────────

def test_suche_filtert(page):
    page.fill("#searchInput", "Beta")
    page.wait_for_timeout(350)
    assert page.locator(".anime-card").count() == 1


def test_kategorie_tab_filtert(page):
    page.click("button[data-tab='kommende-dubs']")
    page.wait_for_timeout(200)
    assert page.locator(".anime-card").count() == 1
    assert "Alpha" in page.locator(".anime-card").first.inner_text()


def test_genre_tag_setzt_den_filter(page):
    page.locator(".tag", has_text="Comedy").first.click()
    page.wait_for_timeout(250)
    assert page.locator("#genreSelect").input_value() == "Comedy"
    assert page.locator(".anime-card").count() == 1


def test_filter_chip_setzt_zurueck(page):
    page.fill("#searchInput", "Beta")
    page.wait_for_timeout(350)
    page.click("[data-clear='all']")
    page.wait_for_timeout(250)
    assert page.locator(".anime-card").count() == 4


def test_leeres_ergebnis_zeigt_hinweis(page):
    page.fill("#searchInput", "gibtesnicht")
    page.wait_for_timeout(350)
    assert page.locator(".empty").is_visible()


def test_einstellungen_ueberleben_einen_reload(page):
    page.fill("#searchInput", "Gamma")
    page.select_option("#sortSelect", "title_asc")
    page.select_option("#pageSizeSelect", "48")
    page.click("button[data-tab='aktuelle-dubs']")
    page.wait_for_timeout(400)

    page.reload()
    page.wait_for_selector(".anime-card", timeout=15000)

    assert page.locator("#searchInput").input_value() == "Gamma"
    assert page.locator("#sortSelect").input_value() == "title_asc"
    assert page.locator("#pageSizeSelect").input_value() == "48"
    assert page.eval_on_selector(".tab-btn.active", "n => n.dataset.tab") == "aktuelle-dubs"


# ─── Bedienung ────────────────────────────────────────────────────────────────

def test_slash_fokussiert_die_suche(page):
    page.keyboard.press("/")
    assert page.evaluate("document.activeElement.id") == "searchInput"


def test_escape_schliesst_das_modal(page):
    page.locator(".anime-card").first.click()
    page.wait_for_selector("#detailsModal.active")
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    assert not page.locator("#detailsModal").evaluate("n => n.classList.contains('active')")


def test_modal_zeigt_fakten_und_links(page):
    page.locator(".anime-card", has_text="Beta Legende").first.click()
    page.wait_for_selector("#detailsModal.active")
    body = page.locator("#modalBody").inner_text()
    assert "Studio Zwei" in body
    assert "8.2" in body            # Bewertung 82 → 8.2
    assert page.locator("#modalBody a[href*='anisearch.de']").count() == 1


def test_watchlist_merkt_sich_anime(page):
    page.locator(".anime-card").first.locator(".card-fav").click()
    page.wait_for_timeout(250)
    assert page.locator("#watchlistCount").inner_text() == "1"

    page.reload()
    page.wait_for_selector(".anime-card", timeout=15000)
    page.click("button[data-tab='watchlist']")
    page.wait_for_timeout(250)
    assert page.locator(".anime-card").count() == 1


def test_thema_laesst_sich_umschalten(page):
    page.click("#themeBtn")
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    page.click("#themeBtn")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"


def test_listenansicht_schaltet_um(page):
    page.click("button[data-view='list']")
    page.wait_for_timeout(200)
    assert "list" in page.locator("#contentArea").get_attribute("class")


def test_keine_javascript_fehler(browser, site):
    context = browser.new_context(locale="de-DE")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(site)
    page.wait_for_selector(".anime-card", timeout=15000)
    page.locator(".anime-card").first.click()
    page.wait_for_timeout(400)
    context.close()
    assert errors == []


def test_demo_modus_ohne_datenquelle(browser):
    """Ohne erreichbare Datei zeigt die Seite klar gekennzeichnete Demo-Daten."""
    context = browser.new_context(locale="de-DE")
    page = context.new_page()
    page.route("**/anime_data.json", lambda route: route.abort())
    page.route("**/raw.githubusercontent.com/**", lambda route: route.abort())
    page.goto(f"file://{os.path.join(ROOT, 'index.html')}")
    page.wait_for_selector(".anime-card", timeout=15000)

    assert "Demo" in page.locator("#apiStatus").inner_text()
    assert "Demo" in page.locator(".anime-card").first.inner_text()
    context.close()
