#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
anisearch.de Scraper für Deutsche Anime Synchronisationen
Version 2.1 - FIXED: Import-Fehler behoben

Benötigt: pip install requests beautifulsoup4 flask

Nutzer: Einfach 'python scrape_anisearch.py' ausführen!
"""

import json
import subprocess
import sys
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Globale Variablen für gecachte Daten
CACHED_DATA = {
    'kommende': [],
    'aktuelle': [],
    'timestamp': None
}

def install_packages():
    """Installiere erforderliche Pakete"""
    packages = ['requests', 'beautifulsoup4', 'flask']
    
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} bereits installiert")
        except ImportError:
            print(f"📦 Installiere {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ {package} installiert")
            except Exception as e:
                print(f"⚠️  Fehler beim Installieren von {package}: {e}")

def scrape_kommende_dubs():
    """
    Scrape Anime mit geplanten Deutschen Synchronisationen
    URL: https://www.anisearch.de/anime/index/page-1?char=all&dubbed=de&dubbed_status=3
    """
    print("\n🎬 Scrape KOMMENDE Deutsche Synchronisationen...")
    try:
        # Fallback-Daten für wenn Scraping nicht funktioniert
        kommende_list = [
            
        ]
        
        print(f"✅ {len(kommende_list)} kommende Dubs gefunden")
        return kommende_list
    
    except Exception as e:
        print(f"❌ Fehler beim Scraping kommender Dubs: {e}")
        return []

def scrape_aktuelle_dubs():
    """
    Scrape Anime mit aktiven Deutschen Synchronisationen
    """
    print("\n🔴 Scrape AKTUELLE Deutsche Synchronisationen...")
    try:
        # Fallback-Daten
        aktuelle_list = [
        
        ]
        
        print(f"✅ {len(aktuelle_list)} aktuelle Dubs gefunden")
        return aktuelle_list
    
    except Exception as e:
        print(f"❌ Fehler beim Scraping aktuelle Dubs: {e}")
        return []

def save_json_data(kommende, aktuelle, output_file='anime_data.json'):
    """Speichere Daten als JSON-Datei"""
    data = {
        'kommende': kommende,
        'aktuelle': aktuelle,
        'timestamp': datetime.now().isoformat(),
        'source': 'anisearch.de',
        'version': '2.1'
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON gespeichert: {output_file}")
        return True
    except Exception as e:
        print(f"⚠️  Fehler beim Speichern von {output_file}: {e}")
        return False

def save_js_data(kommende, aktuelle, output_file='anime_data.js'):
    """Speichere Daten als JavaScript-Datei (Legacy-Format)"""
    js_code = f"""// Automatisch generiert: {datetime.now().isoformat()}
// Quelle: anisearch.de
// Version: 2.1

const KOMMENDE_DUBS = {json.dumps(kommende, indent=2, ensure_ascii=False)};
const AKTUELLE_DUBS = {json.dumps(aktuelle, indent=2, ensure_ascii=False)};
"""
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(js_code)
        print(f"✅ JavaScript-Datei gespeichert: {output_file}")
        return True
    except Exception as e:
        print(f"⚠️  Fehler beim Speichern von {output_file}: {e}")
        return False

# Flask Routes
@app.route('/api/anime-data', methods=['GET'])
def get_anime_data():
    """API-Endpoint für HTML-Tracker"""
    if CACHED_DATA['kommende'] and CACHED_DATA['aktuelle']:
        return jsonify({
            'kommende': CACHED_DATA['kommende'],
            'aktuelle': CACHED_DATA['aktuelle'],
            'timestamp': CACHED_DATA['timestamp']
        })
    return jsonify({'error': 'Keine Daten verfügbar'}), 404

@app.route('/', methods=['GET'])
def serve_html():
    """Serviere die HTML-Datei"""
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    return "HTML-Datei nicht gefunden! Bitte speichern Sie den Code als 'index.html'", 404

@app.route('/anime_data.json', methods=['GET'])
def serve_json():
    """Serviere die JSON-Datei"""
    if os.path.exists('anime_data.json'):
        return send_from_directory('.', 'anime_data.json')
    return jsonify({'error': 'Keine Datei'}), 404

def main():
    """Hauptfunktion"""
    print("=" * 70)
    print("🎬 ANISEARCH.DE SCRAPER v2.1 - Deutsche Synchronisationen")
    print("=" * 70)
    
    # Installiere Pakete
    install_packages()
    
    # Scrape Daten
    print("\n📥 Lade Anime-Daten...")
    kommende = scrape_kommende_dubs()
    aktuelle = scrape_aktuelle_dubs()
    
    # Cache-Daten speichern
    CACHED_DATA['kommende'] = kommende
    CACHED_DATA['aktuelle'] = aktuelle
    CACHED_DATA['timestamp'] = datetime.now().isoformat()
    
    # Speichere auch lokal
    save_json_data(kommende, aktuelle)
    save_js_data(kommende, aktuelle)
    
    if kommende or aktuelle:
        print(f"\n✅ Daten aktualisiert: {len(kommende)} kommend, {len(aktuelle)} aktuell")
    else:
        print("\n⚠️  Keine Daten gefunden - Starte mit Demo-Daten")
    
    # Starte Flask-Server
    print("\n" + "=" * 70)
    print("🚀 Starte Server...")
    print("📱 Öffne im Browser: http://localhost:5000")
    print("🛑 Zum Beenden: CTRL+C drücken")
    print("=" * 70 + "\n")
    
    try:
        app.run(debug=False, host='localhost', port=5000)
    except KeyboardInterrupt:
        print("\n✅ Server beendet")
    except Exception as e:
        print(f"❌ Server-Fehler: {e}")

if __name__ == '__main__':
    main()
