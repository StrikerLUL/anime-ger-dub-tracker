# 🎬 Anime Ger Dub Tracker

Verfolgt deutsche Anime-Synchronisationen auf [anisearch.de](https://www.anisearch.de) –
täglich automatisch aktualisiert per GitHub Actions und als Datenquelle für
[meine-anime-welt.de](https://meine-anime-welt.de).

## 📋 Inhaltsverzeichnis

- [Wie es funktioniert](#-wie-es-funktioniert)
- [Datenformat](#-datenformat)
- [Garantien der Datenpipeline](#-garantien-der-datenpipeline)
- [Projektstruktur](#-projektstruktur)
- [Lokal starten](#-lokal-starten)
- [Website-Anbindung](#-website-anbindung)
- [Tests](#-tests)
- [Bekannte Einschränkungen](#-bekannte-einschränkungen)
- [Troubleshooting](#-troubleshooting)
- [Beitragen](#-beitragen)

## 🔄 Wie es funktioniert

```
GitHub Actions (täglich 06:00 UTC)
   ↓
scraper_standalone.py  →  anisearch_scraper.py  →  anisearch.de auslesen (Playwright)
   ↓
Kategorien zusammenführen + entdoppeln
   ↓
anime_data.json  (nur bei echter Datenänderung neu geschrieben)
   ↓
check_data.py  (Duplikat-Prüfung – schlägt fehl, statt Doppeltes zu veröffentlichen)
   ↓                                    ↓
git commit + push                   FTP-Upload → meine-anime-welt.de
   ↓
Frontend (HTML) lädt anime_data.json und zeigt die Anime an
```

Lokal lässt sich derselbe Ablauf mit einem kleinen Flask-Server ausführen
(`scrape_anisearch_fixed.py`) – er nutzt exakt dieselbe Logik, damit es keine
zweite Wahrheit über die Daten gibt.

## 📦 Datenformat

`anime_data.json` – die einzige Datendatei des Projekts:

```json
{
  "kommende":      [ { "id": 19245, "title": "…", "url": "…", "image": "…",
                       "info": "TV-Serie, 12 (2026)", "year": 2026,
                       "type": "TV-Serie", "status": "kommende" } ],
  "aktuelle":      [ … ],
  "abgeschlossen": [ … ],

  "timestamp":       "2026-09-01T16:27:20Z",
  "data_changed_at": "2026-09-01T16:27:20Z",
  "data_hash":       "2969a3b6…",
  "counts":          { "kommende": 35, "aktuelle": 40, "abgeschlossen": 0 },
  "total":           75,
  "source":          "anisearch.de",
  "version":         "5.0",
  "warnings":        []
}
```

| Feld | Bedeutung |
|------|-----------|
| `kommende` / `aktuelle` / `abgeschlossen` | Die drei Kategorien. **Überschneidungsfrei** – jeder Anime steht in genau einer davon. |
| `status` | Kategorie des Eintrags, direkt am Anime. |
| `timestamp` | Zeitpunkt der letzten **inhaltlichen** Änderung (nicht des letzten Laufs). |
| `data_changed_at` | Identisch zu `timestamp`, sprechender benannt. |
| `data_hash` | SHA-256 über die reinen Anime-Daten. Damit erkennt das Frontend, ob sich wirklich etwas geändert hat. |
| `counts` / `total` | Vorgezählte Anzahlen. |
| `warnings` | Hinweise des Scrapers, z. B. wenn anisearch.de einen Filter ignoriert hat. |

> Die Felder `kommende`, `aktuelle`, `abgeschlossen`, `timestamp`, `source` und
> `version` gab es schon vorher und sie behalten ihre Bedeutung – bestehende
> Einbindungen laufen unverändert weiter.

## ✅ Garantien der Datenpipeline

**1. Kein Anime wird doppelt gespeichert.**
Liefert anisearch.de denselben Eintrag in mehreren Abfragen, gewinnt die
Kategorie mit der höheren Priorität (`kommende` → `aktuelle` → `abgeschlossen`);
in allen anderen wird er entfernt. `check_data.py` prüft das anschließend noch
einmal und bricht den Lauf ab, falls doch ein Duplikat durchkommt.

**2. Nichts wird ohne Grund neu gespeichert.**
Der Scraper berechnet einen Hash über die Anime-Daten und vergleicht ihn mit der
vorhandenen Datei. Sind die Daten gleich, bleibt `anime_data.json` **Byte für
Byte unverändert** – kein Diff, kein Commit, keine endlos wachsende Historie.
Früher änderte sich täglich der Zeitstempel und erzeugte auch dann einen Commit,
wenn sich kein einziger Anime geändert hatte.

**3. Einträge ohne ID gehen nicht verloren.**
Fehlt die anisearch-ID, wird auf URL bzw. Titel ausgewichen. Früher fielen alle
diese Einträge auf denselben Schlüssel `0` zusammen und wurden verworfen.

**4. Halb geschriebene Dateien gibt es nicht.**
Geschrieben wird in eine temporäre Datei, die anschließend atomar an ihren Platz
verschoben wird.

## 📁 Projektstruktur

```
anime-ger-dub-tracker/
├── anisearch_scraper.py              # Scraping- & Datenlogik (gemeinsame Basis)
├── scraper_standalone.py             # Einstieg für GitHub Actions
├── scrape_anisearch_fixed.py         # Lokaler Flask-Server + Frontend-Auslieferung
├── check_data.py                     # Prüft anime_data.json auf Duplikate
├── test_data_pipeline.py             # Tests der Datenlogik (ohne Netzwerk)
├── test_filters.py                   # Playwright-Test: Filter & localStorage
├── test_shortcuts.py                 # Playwright-Test: Tastenkürzel
├── test_tooltip.py                   # Playwright-Test: Tooltips
├── Anime Synchro Tracker v11.0.1.html # Frontend
├── anime_data.json                   # Die Daten
├── requirements_actions.txt          # Abhängigkeiten für CI
├── SERVER STARTEN.bat                # Windows-Doppelklickstart
└── .github/workflows/scrape.yml      # Täglicher Scraping-Workflow
```

## 💻 Lokal starten

**Voraussetzungen:** Python 3.8+, moderner Browser.

```bash
git clone https://github.com/StrikerLUL/anime-ger-dub-tracker.git
cd anime-ger-dub-tracker

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install flask playwright pytest
python -m playwright install chromium
```

**Mit Server (empfohlen):**

```bash
python scrape_anisearch_fixed.py
```

Auswahl im Menü:

| Option | Verhalten |
|--------|-----------|
| `1` | Scrapt anisearch.de und startet den Server (alle 6 h automatisch neu) |
| `2` | Startet nur den Server mit den gespeicherten Daten |
| `3` | Scrapt nur, kein Server |

Danach <http://localhost:5000> öffnen. Unter Windows genügt ein Doppelklick auf
`SERVER STARTEN.bat`.

**Nur die Daten aktualisieren:**

```bash
python scraper_standalone.py     # schreibt anime_data.json
python check_data.py             # prüft das Ergebnis
```

**Ohne Server:** Die HTML-Datei lässt sich auch direkt öffnen – sie lädt
`anime_data.json` aus demselben Verzeichnis und fällt notfalls auf die Datei in
diesem GitHub-Repository zurück.

### API des lokalen Servers

| Endpunkt | Beschreibung |
|----------|--------------|
| `GET /` | Frontend |
| `GET /api/anime-data` | Aktuelle Daten, gleiches Format wie `anime_data.json` |
| `GET /api/status` | Anzahlen, Zeitstempel, Warnungen, Scraping-Status |
| `GET /api/refresh` | Startet einen Scraping-Lauf im Hintergrund |
| `GET /anime_data.json` | Die gespeicherte Datei |

## 🌐 Website-Anbindung

Das Frontend erkennt selbst, wo es läuft:

* **Gehostet** (z. B. meine-anime-welt.de): lädt `anime_data.json` von der
  eigenen Domain, ersatzweise direkt von GitHub. Es wird **kein** `localhost`
  kontaktiert – das ging vorher ohnehin nicht und erzeugte alle 30 Sekunden eine
  Fehlermeldung. Aktualisierung alle 15 Minuten.
* **Lokal** (`localhost` oder direkt geöffnete Datei): nutzt zusätzlich den
  Flask-Server für Live-Daten und aktualisiert alle 30 Sekunden.

### Automatischer Upload per FTP

Sind in den Repository-Secrets `FTP_HOST`, `FTP_USER` und `FTP_PASS` hinterlegt,
lädt der Workflow `anime_data.json` nach jedem Lauf auf den Webspace.
`FTP_PATH` ist optional (Standard: `/htdocs/`).

Ohne FTP funktioniert es ebenfalls: Das Frontend lädt die Datei dann direkt aus
diesem Repository (`GITHUB_RAW_URL` in der HTML-Datei).

## 🧪 Tests

```bash
python -m pytest test_data_pipeline.py -q     # Datenlogik, ohne Netzwerk
python -m pytest -q                           # zusätzlich die Playwright-Tests
```

`test_data_pipeline.py` läuft in GitHub Actions vor jedem Scraping-Lauf und
deckt Deduplizierung, Schlüsselbildung, Hashing und das Schreibverhalten ab –
inklusive der Prüfung, dass die ausgelieferte `anime_data.json` duplikatfrei ist.

## ⚠️ Bekannte Einschränkungen

**Der `dubbed_status`-Filter von anisearch.de greift derzeit nicht.**
Die Abfragen für „laufende" und „abgeschlossene" Syncros liefern dieselbe
Ergebnisliste. Genau daher kamen die doppelten Daten: dieselben 40 Anime wurden
zweimal gespeichert und auf der Website zweimal angezeigt.

Die Pipeline speichert jetzt nichts mehr doppelt und meldet das Problem in
`warnings` sowie als Warnung im Actions-Log. Solange der Filter nicht greift,
bleibt `abgeschlossen` leer und der entsprechende Tab im Frontend ausgeblendet –
lieber eine Kategorie weniger als dieselben Anime zweimal.

**Zum Beheben** die Filter-URLs in `anisearch_scraper.py` anpassen:

```python
CATEGORY_PARAMS = {
    "kommende":      "char=all&dubbed=de&dubbed_status=3&sort=date&order=asc",
    "aktuelle":      "char=all&dubbed=de&dubbed_status=2&sort=date&order=desc",
    "abgeschlossen": "char=all&dubbed=de&dubbed_status=1&sort=date&order=desc",
}
```

Vorgehen: die gewünschte Filterung auf anisearch.de im Browser einstellen, die
entstehende URL kopieren und den Teil hinter dem `?` hier eintragen. Nach einem
Lauf zeigt `python check_data.py`, ob die Kategorien nun unterschiedlich sind –
die Warnung „Filter greift nicht" verschwindet dann.

**Weitere Punkte**

* Scraping kann brechen, wenn anisearch.de sein HTML ändert (Selektoren in
  `parse_anime_list`).
* Die Anzahl der Listenseiten pro Kategorie ist begrenzt (`CATEGORY_MAX_PAGES`).
* Keine Echtzeit-Updates – die Daten werden einmal täglich aktualisiert.

## 🐛 Troubleshooting

**`ModuleNotFoundError: No module named 'flask'`**
```bash
pip install flask playwright
python -m playwright install chromium
```

**Port 5000 belegt** – Port in `scrape_anisearch_fixed.py` ändern:
```python
app.run(debug=False, host="localhost", port=5001, use_reloader=False)
```

**Die Website zeigt alte Daten**
`data_changed_at` in `anime_data.json` prüfen. Steht dort ein alter Zeitpunkt,
hat sich seitdem tatsächlich nichts geändert – das ist gewollt. Ob der Workflow
lief, zeigt der Actions-Tab.

**Anime tauchen doppelt auf**
Sollte nicht mehr vorkommen. Falls doch: `python check_data.py` ausführen – die
Ausgabe nennt die betroffenen Titel und Kategorien.

**Scraper findet nichts**
anisearch.de hat vermutlich das Seitenlayout geändert. Bitte ein Issue mit der
Ausgabe des Laufs öffnen.

## 🤝 Beitragen

1. Repository **forken**
2. **Feature-Branch** erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen **committen** (`git commit -m 'Add some AmazingFeature'`)
4. Zum Branch **pushen** (`git push origin feature/AmazingFeature`)
5. **Pull Request** öffnen

Bitte vorher `python -m pytest test_data_pipeline.py -q` laufen lassen.

## 🔐 Sicherheit & Datenschutz

* Es werden **keine personenbezogenen Daten** gespeichert.
* Alle Anime-Daten stammen von anisearch.de (öffentlich zugänglich).
* Außer anisearch.de (Scraping) und GitHub (Datei-Rückfallebene) werden keine
  externen Dienste kontaktiert.
* Bitte die Nutzungsbedingungen von anisearch.de beachten und den Scraper nicht
  häufiger als nötig laufen lassen.

---

**Made with ❤️ for Anime Fans**

*Dieses Projekt ist nicht offiziell mit anisearch.de verbunden.*
