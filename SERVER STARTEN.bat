@echo off
chcp 65001 > nul
title Anime Ger Dub Tracker - Server
echo ============================================================
echo   ANIME GER DUB TRACKER - lokaler Server
echo ============================================================
echo.
echo  Was jetzt passiert:
echo  1. Python-Pakete werden geprueft (flask, playwright)
echo  2. Chromium wird im Hintergrund gestartet
echo  3. anisearch.de, AniList und die News-Feeds werden abgefragt
echo  4. Dein Browser oeffnet sich automatisch auf dem Tracker
echo.
echo  Server:      http://localhost:5000
echo  Daten-API:   http://localhost:5000/api/anime-data
echo  Aktualisieren: http://localhost:5000/api/refresh
echo  Status:      http://localhost:5000/api/status
echo.
echo  Zum Beenden: CTRL+C druecken
echo ============================================================
echo.

REM Kurz warten, dann Browser oeffnen (der Server braucht ein paar Sekunden)
start "" /B cmd /C "timeout /t 4 /nobreak > nul && start http://localhost:5000"

python scrape_anisearch_fixed.py

echo.
echo Server wurde beendet.
pause
