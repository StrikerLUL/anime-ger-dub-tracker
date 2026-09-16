<div align="center">

# 🎬 Anime Ger Dub Tracker

**Welche Anime bekommen eine deutsche Synchronisation?**

Täglich automatisch aktualisiert aus mehreren Quellen, entdoppelt, aufgeräumt –
und als `anime_data.json` direkt in [meine-anime-welt.de](https://meine-anime-welt.de) eingebunden.

[![Daten aktualisieren](https://github.com/StrikerLUL/anime-ger-dub-tracker/actions/workflows/scrape.yml/badge.svg)](https://github.com/StrikerLUL/anime-ger-dub-tracker/actions/workflows/scrape.yml)
[![Tests](https://github.com/StrikerLUL/anime-ger-dub-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/StrikerLUL/anime-ger-dub-tracker/actions/workflows/tests.yml)
[![Aufräumen](https://github.com/StrikerLUL/anime-ger-dub-tracker/actions/workflows/retention.yml/badge.svg)](https://github.com/StrikerLUL/anime-ger-dub-tracker/actions/workflows/retention.yml)

</div>

---

## 📋 Inhalt

- [Was der Tracker macht](#-was-der-tracker-macht)
- [Datenquellen](#-datenquellen)
- [Aufbewahrung – nichts bleibt ewig liegen](#-aufbewahrung--nichts-bleibt-ewig-liegen)
- [Datenformat](#-datenformat)
- [Website-Anbindung](#-website-anbindung)
- [Garantien der Pipeline](#-garantien-der-pipeline)
- [Frontend](#-frontend)
- [Lokal starten](#-lokal-starten)
- [Kommandozeile](#-kommandozeile)
- [Einstellungen](#-einstellungen)
- [Projektstruktur](#-projektstruktur)
- [Tests](#-tests)
- [Automatisierung](#-automatisierung)
- [Bekannte Einschränkungen](#-bekannte-einschränkungen)
- [Troubleshooting](#-troubleshooting)
- [Beitragen](#-beitragen)
- [Sicherheit & Datenschutz](#-sicherheit--datenschutz)

---

## 🔄 Was der Tracker macht

```
 aniSearch.de ──┐
 AniList       ─┤
 MyAnimeList   ─┼─→ zusammenführen → entdoppeln → aufbewahren → anime_data.json
 News-Feeds    ─┘                                                     │
                                                          ┌───────────┴───────────┐
                                                    Git-Commit            FTP-Upload
                                                          │                       │
                                                    GitHub Raw          meine-anime-welt.de
                                                          └───────────┬───────────┘
                                                                 Frontend (index.html)
```

Ein Lauf dauert wenige Minuten, läuft täglich um 06:00 UTC und schreibt die
Datei **nur dann neu, wenn sich wirklich etwas geändert hat**.

## 📡 Datenquellen

| Quelle | Was sie beisteuert | Zugang |
|--------|--------------------|--------|
| **[aniSearch.de](https://www.anisearch.de)** | Die eigentliche Information: welcher Anime bekommt eine **deutsche Synchro** und in welchem Status. Bestimmt die drei Kategorien. | Playwright (die Listen werden per JavaScript aufgebaut) |
| **[AniList](https://anilist.co)** | Episodenzahl, Genres, Studios, Bewertung, hochauflösende Cover, Links | GraphQL-API, **kein API-Key**, mehrere Titel pro Anfrage gebündelt |
| **[MyAnimeList](https://myanimelist.net) (via [Jikan](https://jikan.moe))** | Dieselben Fakten – aber nur für Anime, die AniList nicht kennt | REST-API, **kein API-Key** |
| **Deutsche Anime-News-Feeds** | Meldungen zu neuen Synchros (`news`-Bereich der Datei und der Website) | RSS/Atom |

**Warum mehrere Quellen?** aniSearch.de weiß als einzige Quelle verlässlich
über *deutsche* Synchros Bescheid, liefert auf den Listenseiten aber kaum
Details. AniList und MyAnimeList füllen diese Lücken, ohne die Kategorien
anzufassen – bei ihnen zählen ausschließlich Fakten (Zahlen, Genres, Studios,
Links), keine fremden Beschreibungstexte.

Jede Quelle läuft in ihrer eigenen Fehlerbehandlung: **fällt eine aus, läuft der
Rest weiter.** Ist aniSearch.de nicht erreichbar, bleibt der vorhandene
Datenbestand unangetastet, statt die Website leerzuräumen.

> Jeder Anime wird **einmal** nachgeschlagen; danach stehen seine Zusatzdaten in
> der Datei. Das hält die Zahl der API-Anfragen klein und die Quellen freundlich
> gestimmt.

## 🗃️ Aufbewahrung – nichts bleibt ewig liegen

Früher wuchs `anime_data.json` immer weiter: Was einmal drinstand, blieb drin.
Jetzt räumt der Tracker selbst auf – nach vier Regeln:

| Regel | Standard | Was passiert |
|-------|----------|--------------|
| **Verschwunden = gelöscht** | 14 Tage Karenz | Liefert keine Quelle einen Anime mehr, bekommt er `missing_since`. Nach der Karenz fliegt er raus. Die Karenz verhindert, dass ein einzelner Fehllauf die halbe Datei leert. |
| **Höchstalter** | 365 Tage | Jeder Eintrag hat ein `expires_at` (erstes Auftauchen + Höchstalter). Danach wird er entfernt – auch wenn die Quelle ihn noch führt. |
| **Rückkehrsperre** | 90 Tage | Ein wegen Höchstalter entfernter Anime kommt nicht sofort zurück. Sonst stünde er am nächsten Tag wieder drin und erzeugte jeden Tag einen Commit. |
| **Obergrenze je Kategorie** | 400 Einträge | Mehr wird nicht gespeichert; die ältesten Jahrgänge fallen weg. Hält die Datei auch dann klein, wenn eine Quelle plötzlich Tausende Einträge liefert. |

News verschwinden schneller: **30 Tage**, höchstens **40 Meldungen**.

Alle Werte sind [einstellbar](#-einstellungen), ohne Code anzufassen. Zusätzlich
läuft jeden Montag ein eigener Aufräum-Workflow – so verschwinden alte Daten
auch dann, wenn der Scraper einmal länger klemmt.

```bash
python -m tracker prune     # von Hand aufräumen, ohne zu scrapen
```

## 📦 Datenformat

`anime_data.json` – die einzige Datendatei des Projekts, direkt im
Repository-Wurzelverzeichnis (die Website liest genau diesen Pfad).

```jsonc
{
  "kommende":      [ /* Anime, siehe unten */ ],
  "aktuelle":      [ ... ],
  "abgeschlossen": [ ... ],
  "news":          [ { "title": "…", "url": "…", "source": "anime2you.de",
                       "published": "2026-09-15T08:00:00Z", "summary": "…" } ],

  "timestamp":       "2026-09-16T10:00:00Z",   // letzte inhaltliche Änderung
  "data_changed_at": "2026-09-16T10:00:00Z",   // identisch, sprechender benannt
  "updated_at":      "2026-09-16T10:00:00Z",   // wann die Datei zuletzt geschrieben wurde
  "data_hash":       "b174400f…",              // SHA-256 über die reinen Anime-Daten
  "counts":          { "kommende": 34, "aktuelle": 200, "abgeschlossen": 0, "news": 6 },
  "total":           234,
  "source":          "anisearch.de",           // Hauptquelle (unverändert)
  "sources":         ["anilist", "anisearch", "jikan", "news"],
  "version":         "6.0",
  "retention":       { "max_age_days": 365, "stale_grace_days": 14,
                       "max_entries_per_category": 400, "news_max_age_days": 30 },
  "scraping":        false,
  "warnings":        [],
  "retired":         { "id:12345": "2026-12-15T00:00:00Z" }   // Rückkehrsperre
}
```

Ein Anime-Eintrag:

```jsonc
{
  "id": 19245,                                    // aniSearch-ID
  "title": "A New Dawn",
  "url": "https://www.anisearch.de/anime/19245,…",
  "image": "https://cdn.anisearch.de/…_400.webp",
  "info": "Film, 1 (2026)",
  "year": 2026,
  "type": "Film",
  "status": "kommende",                           // = Kategorie des Eintrags

  // neu ab Version 6.0 – alles optional:
  "episodes": 12,
  "genres": ["Action", "Drama"],
  "studios": ["Studio XY"],
  "score": 82,                                    // 0–100
  "season": 2026,
  "external": { "anilist": 21, "mal": 30,
                "anilist_url": "…", "mal_url": "…" },
  "first_seen": "2026-09-16T10:00:00Z",           // seit wann im Tracker
  "expires_at": "2027-09-16T10:00:00Z",           // wann er spätestens verschwindet
  "missing_since": "2026-09-14T10:00:00Z"         // nur, wenn keine Quelle ihn mehr liefert
}
```

> **Abwärtskompatibel.** `kommende`, `aktuelle`, `abgeschlossen`, `timestamp`,
> `source` und `version` gibt es weiterhin mit derselben Bedeutung, und jeder
> Anime hat nach wie vor `id`, `title`, `url`, `image`, `info`, `year`, `type`
> und `status`. Bestehende Einbindungen laufen unverändert weiter – alles Neue
> kommt zusätzlich dazu.

## 🌐 Website-Anbindung

Die Datei liegt nach jedem Lauf an drei Stellen:

| Ort | URL | Wofür |
|-----|-----|-------|
| Eigener Webspace | `https://meine-anime-welt.de/anime_data.json` | Die schnelle Hauptquelle (per FTP hochgeladen) |
| GitHub Raw | `https://raw.githubusercontent.com/StrikerLUL/anime-ger-dub-tracker/main/anime_data.json` | Rückfallebene, falls der FTP-Upload nicht eingerichtet ist |
| Lokal | `http://localhost:5000/api/anime-data` | Beim Entwickeln |

So liest eine Website die Daten:

```js
const res  = await fetch('anime_data.json', { cache: 'no-store' });
const data = await res.json();

const alle = [...data.kommende, ...data.aktuelle, ...data.abgeschlossen];
// Jeder Anime steht garantiert in genau einer Kategorie.

// Nur neu laden, wenn sich wirklich etwas geändert hat:
if (data.data_hash !== zuletztGesehenerHash) { neuRendern(alle); }
```

### FTP-Upload einrichten (optional)

Sind die Repository-Secrets `FTP_HOST`, `FTP_USER` und `FTP_PASS` gesetzt, lädt
der Workflow `anime_data.json` nach jedem Lauf hoch. `FTP_PATH` ist optional
(Standard `/htdocs/`). Ohne FTP funktioniert alles genauso – das Frontend fällt
dann auf GitHub Raw zurück.

## ✅ Garantien der Pipeline

**1. Kein Anime steht doppelt in der Datei.**
Liefert aniSearch.de denselben Eintrag in mehreren Abfragen, gewinnt die
Kategorie mit der höheren Priorität (`kommende` → `aktuelle` → `abgeschlossen`).
`python -m tracker check` prüft das anschließend noch einmal und bricht ab,
bevor etwas Doppeltes veröffentlicht wird.

**2. Nichts wird ohne Grund neu geschrieben.**
Verglichen wird der komplette Inhalt. Gleiche Daten → Datei bleibt **Byte für
Byte** identisch → kein Diff, kein Commit, keine endlos wachsende Historie.

**3. Einträge ohne ID gehen nicht verloren.**
Fehlt die aniSearch-ID, wird auf URL bzw. Titel ausgewichen.

**4. Halb geschriebene Dateien gibt es nicht.**
Geschrieben wird in eine temporäre Datei, die anschließend atomar an ihren Platz
verschoben wird.

**5. Eine kaputte Quelle kippt den Lauf nicht.**
Jede Quelle ist einzeln abgesichert. Liefert aniSearch.de gar nichts – oder
verdächtig wenig (unter 50 % des Bestands) – wird **nichts** als verschwunden
markiert und der Bestand unverändert behalten.

**6. Was veröffentlicht wird, wurde geprüft.**
`check` kontrolliert Duplikate, Pflichtfelder, Zählerstände, den Hash und die
Aufbewahrungsregeln. Fällt etwas durch, gibt es keinen Commit.

## 🖥️ Frontend

`index.html` – eine einzige Datei, ohne Build-Schritt, ohne externe Skripte oder
Schriftarten. Funktioniert per Doppelklick, über den lokalen Server und auf
jedem Webspace (auch GitHub Pages).

* **Hell & Dunkel** – folgt dem System, umschaltbar, wird gemerkt
* **Suche** über Titel, Genre, Studio und Format
* **Filter** nach Jahr, Format und Genre – als anklickbare Chips, Genre-Tags auf
  jeder Karte
* **Sortierung** nach Jahr, Titel, Bewertung oder Zeitpunkt der Aufnahme
* **Kachel- und Listenansicht**, Seitenblättern, Skeleton-Ladezustand
* **Watchlist** mit Export/Import als JSON (lokal im Browser gespeichert)
* **Dub-News** aus den RSS-Feeds
* **Detailansicht** mit Fakten, Genres und Links zu aniSearch, AniList und MyAnimeList
* **Tastenkürzel:** <kbd>/</kbd> Suche · <kbd>R</kbd> neu laden · <kbd>W</kbd>
  Watchlist · <kbd>T</kbd> Hell/Dunkel · <kbd>Esc</kbd> schließen
* **Barrierearm:** Tastaturbedienung, ARIA-Rollen, sichtbarer Fokus,
  `prefers-reduced-motion`
* **SEO:** Titel, Description, Open Graph, Twitter Card, JSON-LD, Favicon,
  `theme-color`

Das Frontend erkennt selbst, wo es läuft:

* **Gehostet** – lädt `anime_data.json` von der eigenen Domain, ersatzweise von
  GitHub. Es wird **kein** `localhost` kontaktiert (das ginge ohnehin nicht und
  erzeugte früher am laufenden Band Fehlermeldungen). Neu geprüft wird alle 15 Minuten.
* **Lokal** – nutzt zusätzlich den Flask-Server für Live-Daten, alle 30 Sekunden.
* **Nichts erreichbar** – zeigt klar gekennzeichnete Demo-Einträge, damit
  niemand Platzhalter für echte Dub-Infos hält.

## 💻 Lokal starten

**Voraussetzungen:** Python 3.9+ und ein moderner Browser.

```bash
git clone https://github.com/StrikerLUL/anime-ger-dub-tracker.git
cd anime-ger-dub-tracker

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
python -m playwright install chromium
```

**Mit Server (empfohlen):**

```bash
python scrape_anisearch_fixed.py     # mit Menü
python -m tracker serve              # ohne Menü
```

Danach <http://localhost:5000> öffnen. Unter Windows genügt ein Doppelklick auf
`SERVER STARTEN.bat`.

**Nur die Daten aktualisieren:**

```bash
python -m tracker scrape
python -m tracker check
```

**Ohne alles:** `index.html` einfach doppelklicken – die Datei lädt
`anime_data.json` aus demselben Ordner und fällt notfalls auf GitHub zurück.

### API des lokalen Servers

| Endpunkt | Beschreibung |
|----------|--------------|
| `GET /` | Frontend |
| `GET /api/anime-data` | Aktuelle Daten, gleiches Format wie `anime_data.json` |
| `GET /api/status` | Anzahlen, Zeitstempel, Quellen, Aufbewahrung, Warnungen |
| `GET /api/refresh` | Startet einen Lauf im Hintergrund |
| `GET /anime_data.json` | Die gespeicherte Datei |

## ⌨️ Kommandozeile

```bash
python -m tracker scrape     # Quellen abfragen und Daten aktualisieren
python -m tracker prune      # nur aufräumen (ohne Scraping)
python -m tracker check      # anime_data.json prüfen
python -m tracker info       # Stand und Einstellungen anzeigen
python -m tracker serve      # lokalen Server starten
```

Die gewohnten Skripte gibt es weiterhin – sie rufen dasselbe auf:
`scraper_standalone.py` (= `scrape`), `check_data.py` (= `check`),
`scrape_anisearch_fixed.py` (= `serve` mit Menü).

## ⚙️ Einstellungen

Alles über Umgebungsvariablen, kein Code-Eingriff nötig:

| Variable | Standard | Bedeutung |
|----------|----------|-----------|
| `TRACKER_MAX_AGE_DAYS` | `365` | Höchstalter je Eintrag (Tage) |
| `TRACKER_STALE_GRACE_DAYS` | `14` | Karenz für verschwundene Einträge |
| `TRACKER_TOMBSTONE_DAYS` | `90` | Dauer der Rückkehrsperre |
| `TRACKER_MAX_ENTRIES` | `400` | Obergrenze je Kategorie |
| `TRACKER_NEWS_MAX_AGE_DAYS` | `30` | Höchstalter für News |
| `TRACKER_NEWS_MAX_ITEMS` | `40` | Obergrenze für News |
| `TRACKER_SOURCES` | `anisearch,anilist,jikan,news` | Aktive Quellen |
| `TRACKER_DISABLE_ANILIST` | – | Einzelne Quelle abschalten (`…_JIKAN`, `…_NEWS`, `…_ANISEARCH`) |
| `TRACKER_NEWS_FEEDS` | zwei deutsche Feeds | Eigene RSS-Feeds (Komma-getrennt) |
| `TRACKER_MAX_PAGES` | `5` | Listenseiten je Kategorie |
| `TRACKER_ANILIST_BUDGET` | `240` | Titel je Lauf bei AniList |
| `TRACKER_JIKAN_BUDGET` | `30` | Titel je Lauf bei MyAnimeList |
| `TRACKER_DATA_FILE` | `anime_data.json` | Anderer Pfad für die Datei |

Beispiel:

```bash
TRACKER_MAX_AGE_DAYS=180 TRACKER_SOURCES=anisearch,anilist python -m tracker scrape
```

Im Workflow stehen dieselben Werte oben unter `env:` – dort einmal ändern genügt.

## 📁 Projektstruktur

```
anime-ger-dub-tracker/
├── tracker/                        # die gesamte Logik
│   ├── config.py                   # Einstellungen & Aufbewahrungsregeln
│   ├── models.py                   # Datenmodell, Titelabgleich, Zeitrechnung
│   ├── http.py                     # HTTP-Helfer (nur Standardbibliothek)
│   ├── merge.py                    # Zusammenführen & Entdoppeln
│   ├── retention.py                # Aufbewahrung – alte Daten verschwinden
│   ├── store.py                    # anime_data.json lesen & schreiben
│   ├── pipeline.py                 # der komplette Ablauf
│   ├── check.py                    # Qualitätsprüfung vor der Veröffentlichung
│   ├── server.py                   # lokaler Flask-Server
│   ├── cli.py                      # python -m tracker …
│   └── sources/
│       ├── anisearch.py            # deutsche Synchros (Playwright)
│       ├── anilist.py              # Fakten via GraphQL
│       ├── jikan.py                # Fakten via MyAnimeList
│       └── news.py                 # deutsche Anime-News (RSS/Atom)
├── tests/                          # 128 Tests, davon 22 im echten Browser
├── index.html                      # Frontend (eine Datei, kein Build)
├── anime_data.json                 # die Daten
├── scraper_standalone.py           # Einstieg für GitHub Actions
├── check_data.py                   # Prüfung von Hand
├── scrape_anisearch_fixed.py       # lokaler Server mit Menü
├── anisearch_scraper.py            # Kompatibilitäts-Modul (veraltet)
├── SERVER STARTEN.bat              # Windows-Doppelklickstart
└── .github/workflows/
    ├── scrape.yml                  # täglich: Daten aktualisieren
    ├── retention.yml               # montags: aufräumen
    └── tests.yml                   # bei jedem Push: Tests
```

## 🧪 Tests

```bash
python -m pytest -m "not ui"    # Datenlogik, ohne Netzwerk und Browser (schnell)
python -m pytest                # zusätzlich die Frontend-Tests
```

Die Tests kommen ohne Netzwerk aus – die Quellen werden mit erfundenen Antworten
gefüttert. Abgedeckt sind Entdoppelung, Titelabgleich, Aufbewahrung in allen
Varianten, Schreibverhalten, Prüflogik und das Frontend im echten Browser
(Filter, Watchlist, Modal, Tastenkürzel, Demo-Modus).

Steht Chromium schon an anderer Stelle bereit:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/pfad/zu/chromium python -m pytest -m ui
```

## 🤖 Automatisierung

| Workflow | Wann | Was |
|----------|------|-----|
| `scrape.yml` | täglich 06:00 UTC, manuell | Tests → Quellen abfragen → prüfen → committen → FTP-Upload |
| `retention.yml` | montags 04:30 UTC, manuell | Aufräumen, auch wenn der Scraper klemmt |
| `tests.yml` | bei jedem Push & Pull Request | Tests auf mehreren Python-Versionen + Frontend im Browser |

Beim manuellen Start von `scrape.yml` lässt sich einstellen, welche Quellen
laufen sollen – praktisch zum Ausprobieren.

### GitHub-Topics

Damit das Repository gefunden wird, im GitHub-UI unter *About → ⚙ → Topics*
eintragen:

```
anime  german-dub  ger-dub  anime-tracker  synchronisation  anisearch
anilist  web-scraping  playwright  python  github-actions  json-api
open-data  watchlist
```

## ⚠️ Bekannte Einschränkungen

**Der `dubbed_status`-Filter von aniSearch.de greift derzeit nicht.**
Die Abfragen für „laufende" und „abgeschlossene" Syncros liefern dieselbe
Ergebnisliste. Genau daher kamen früher die doppelten Daten.

Die Pipeline speichert nichts mehr doppelt, meldet das Problem in `warnings` und
teilt die Kategorien behelfsweise nach dem Erscheinungsjahr auf: Anime, deren
Jahrgang mindestens zwei Jahre zurückliegt, gelten als „abgeschlossen". Solche
Einträge sind mit `"status_geschaetzt": true` markiert, und die Website weist
sichtbar darauf hin – eine Schätzung soll nicht wie eine Tatsache aussehen.

**Zum Beheben** die Filter in `tracker/sources/anisearch.py` anpassen:

```python
CATEGORY_PARAMS = {
    "kommende":      "char=all&dubbed=de&dubbed_status=3&sort=date&order=asc",
    "aktuelle":      "char=all&dubbed=de&dubbed_status=2&sort=date&order=desc",
    "abgeschlossen": "char=all&dubbed=de&dubbed_status=1&sort=date&order=desc",
}
```

Vorgehen: die gewünschte Filterung auf aniSearch.de im Browser einstellen, die
entstehende URL kopieren und den Teil hinter dem `?` hier eintragen. Nach einem
Lauf zeigt `python -m tracker check`, ob die Kategorien nun unterschiedlich sind
– die Warnung „Filter greift nicht" verschwindet dann.

**Weitere Punkte**

* Scraping kann brechen, wenn aniSearch.de sein HTML ändert (Selektoren in
  `parse_anime_list`).
* Die Zuordnung zu AniList/MyAnimeList läuft über den Titel. Bei mehrdeutigen
  Titeln wird lieber gar nichts übernommen als etwas Falsches – deshalb fehlen
  bei manchen Anime die Genres.
* Keine Echtzeit-Updates: die Daten werden einmal täglich aktualisiert.

## 🐛 Troubleshooting

**`ModuleNotFoundError: No module named 'flask'`**
```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
```

**Port 5000 belegt**
```bash
python -m tracker serve --port 5001
```

**Die Website zeigt alte Daten**
`data_changed_at` in `anime_data.json` prüfen. Steht dort ein alter Zeitpunkt,
hat sich seitdem tatsächlich nichts geändert – das ist gewollt. `updated_at`
zeigt, wann die Datei zuletzt geschrieben wurde; ob der Lauf stattfand, zeigt
der Actions-Tab.

**Ein Anime ist plötzlich verschwunden**
Wahrscheinlich die Aufbewahrung. `python -m tracker info` zeigt die geltenden
Regeln, `expires_at` am Eintrag das Verfallsdatum. Soll länger aufbewahrt
werden: `TRACKER_MAX_AGE_DAYS` im Workflow erhöhen.

**Anime tauchen doppelt auf**
Sollte nicht mehr vorkommen. Falls doch: `python -m tracker check` ausführen –
die Ausgabe nennt die betroffenen Titel und Kategorien.

**Der Scraper findet nichts**
aniSearch.de hat vermutlich das Seitenlayout geändert. Bitte ein Issue mit der
Ausgabe des Laufs öffnen. Die vorhandenen Daten bleiben in so einem Fall
erhalten – die Website zeigt weiter den letzten Stand.

## 🤝 Beitragen

1. Repository **forken**
2. **Feature-Branch** erstellen (`git checkout -b feature/tolle-idee`)
3. Änderungen **committen**
4. Zum Branch **pushen** und **Pull Request** öffnen

Bitte vorher `python -m pytest -m "not ui"` laufen lassen. Neue Datenlogik ohne
Test wird nicht übernommen – genau diese Tests haben die doppelten Daten
gefunden.

## 🔐 Sicherheit & Datenschutz

* Es werden **keine personenbezogenen Daten** gespeichert. Die Watchlist liegt
  ausschließlich im Browser der Besucher (`localStorage`).
* Alle Anime-Daten stammen aus öffentlich zugänglichen Quellen. Übernommen
  werden nur Fakten und Links, keine fremden Beschreibungstexte.
* Das Frontend lädt **keine** externen Skripte, Schriftarten oder Tracker.
* Es werden keine Zugangsdaten im Repository gespeichert; FTP-Daten liegen in
  GitHub-Secrets.
* Bitte die Nutzungsbedingungen der Quellen beachten und den Scraper nicht
  häufiger laufen lassen als nötig.

---

<div align="center">

**Made with ❤️ for Anime Fans**

*Dieses Projekt ist nicht offiziell mit aniSearch.de, AniList oder MyAnimeList verbunden.*

</div>
