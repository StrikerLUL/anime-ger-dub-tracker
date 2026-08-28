
        // ─── Konfiguration ───────────────────────────────────────────────
        const CONFIG = {
            SERVER_URL:       'http://localhost:5000',
            API_ENDPOINT:     'http://localhost:5000/api/anime-data',
            REFRESH_ENDPOINT: 'http://localhost:5000/api/refresh',
            JSON_CACHE:       'anime_data.json',
            POLL_INTERVAL_MS: 30000,  // 30 Sekunden Auto-Poll
            FETCH_TIMEOUT_MS: 5000,

            // ► GitHub Raw URL für InfinityFree-Hosting
            // Wird täglich von GitHub Actions aktualisiert.
            // Format: https://raw.githubusercontent.com/USERNAME/REPO/main/anime_data.json
            // Setze auf '' um diese Quelle zu deaktivieren.
            GITHUB_RAW_URL: 'https://raw.githubusercontent.com/StrikerLUL/anime-ger-dub-tracker-WORK-IN-PROGRESS/main/anime_data.json',
        };

        // ─── Globaler State ──────────────────────────────────────────────
        function getSafePageSize() {
            try {
                return parseInt(localStorage.getItem('premiumPageSize') || '24');
            } catch (e) {
                console.warn('LocalStorage nicht verfügbar', e);
                // Cannot call showNotification here since DOM might not be fully loaded,
                // and it's called during state initialization.
                return 24;
            }
        }

        const state = {
            animes: [],
            watchlist: [],
            filteredAnimes: [],
            currentPage: 1,
            pageSize: getSafePageSize(),
            currentTab: 'alle',
            dataSource: 'none',  // 'live' | 'cache' | 'demo'
            lastUpdate: null,
            pollTimer: null,
            hasAbgeschlossen: false,
        };

        // Fallback Data updated for UI labels
        const KOMMENDE_DUBS = [
            { title: 'Anne Shirley', year: 2025, episodes: 24, status: 'Upcoming', dub_weeks: 2 },
            { title: 'Assassination Classroom Movie', year: 2026, episodes: 1, status: 'Film', dub_weeks: 3 },
            { title: 'Banana Fish', year: 2018, episodes: 24, status: 'Completed', dub_weeks: 1 },
            { title: 'Bocchi the Rock!', year: 2022, episodes: 12, status: 'Completed', dub_weeks: 2 },
            { title: 'Demon Slayer - Infinity Castle', year: 2025, episodes: 26, status: 'Upcoming', dub_weeks: 1 },
            { title: 'Solo Leveling S2', year: 2024, episodes: 13, status: 'Upcoming', dub_weeks: 4 },
            { title: 'Spy x Family', year: 2022, episodes: 25, status: 'Ongoing', dub_weeks: 3 },
            { title: 'Wind Breaker', year: 2024, episodes: 12, status: 'Ongoing', dub_weeks: 2 }
        ];

        const AKTUELLE_DUBS = [
            { title: 'Jujutsu Kaisen', year: 2020, episodes: 47, status: 'Ongoing', days_ago: 2 },
            { title: 'My Hero Academia', year: 2016, episodes: 120, status: 'Ongoing', days_ago: 5 },
            { title: 'Frieren: Beyond Journey\'s End', year: 2023, episodes: 28, status: 'Completed', days_ago: 1 },
            { title: 'Cyberpunk: Edgerunners', year: 2022, episodes: 10, status: 'Completed', days_ago: 8 },
            { title: 'Chainsaw Man', year: 2022, episodes: 12, status: 'Completed', days_ago: 14 },
            { title: 'Death Note', year: 2006, episodes: 37, status: 'Completed', days_ago: 20 },
            { title: 'Tokyo Ghoul', year: 2014, episodes: 48, status: 'Completed', days_ago: 4 },
            { title: 'One Punch Man', year: 2015, episodes: 24, status: 'Ongoing', days_ago: 10 }
        ];

        function formatTime() {
            return new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute:'2-digit', second:'2-digit' });
        }

        function addLog(message) {
            const logEl = document.getElementById('updateLog');
            if (!logEl) return;
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${formatTime()}]</span> ${message}`;
            logEl.appendChild(entry);
            logEl.scrollTop = logEl.scrollHeight;
            if (logEl.children.length > 30) logEl.removeChild(logEl.firstChild);
        }

        // ─── Datenquellen ─────────────────────────────────────────────

        async function fetchWithTimeout(url, ms) {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), ms);
            try {
                const r = await fetch(url, { signal: controller.signal });
                clearTimeout(timer);
                return r;
            } catch (e) {
                clearTimeout(timer);
                throw e;
            }
        }

        async function loadFromServer() {
            try {
                const response = await fetchWithTimeout(CONFIG.API_ENDPOINT, CONFIG.FETCH_TIMEOUT_MS);
                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }
                const data = await response.json();
                if (data.error) return null;  // Server da, aber Daten noch nicht bereit
                return data;
            } catch (e) {
                /* Server offline */
                showNotification('Fehler beim Verbinden mit dem Server');
            }
            return null;
        }

        async function loadFromCachedJson() {
            // Quelle A: GitHub Raw URL (für InfinityFree-Hosting, immer erreichbar wenn Repo public ist)
            if (CONFIG.GITHUB_RAW_URL) {
                try {
                    const response = await fetchWithTimeout(CONFIG.GITHUB_RAW_URL, 8000);
                    if (!response.ok) {
                        throw new Error(`HTTP Error: ${response.status}`);
                    }
                    const data = await response.json();
                    if (data.kommende || data.aktuelle) {
                        data.source = 'github';
                        return data;
                    }
                } catch (e) {
                    /* GitHub nicht erreichbar */
                    showNotification('Fehler beim Laden der gecachten Daten');
                }
            }

            // Quelle B: Lokale anime_data.json (via Flask-Server oder selber Domain)
            try {
                const response = await fetchWithTimeout(CONFIG.SERVER_URL + '/' + CONFIG.JSON_CACHE, 3000);
                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }
                const data = await response.json();
                if (data.kommende || data.aktuelle) {
                    data.source = 'cache';
                    return data;
                }
            } catch (e) {
                /* kein Server */
                showNotification('Fehler beim Laden der gecachten Daten');
            }
            return null;
        }

        // ─── Normalisierung ───────────────────────────────────────────

        function normalizeAnime(raw, index, type) {
            try {
                const isScraperFormat = raw.info !== undefined;
                return {
                    ...raw,
                    format: raw.type || raw.format || 'Unbekannt',
                    id: raw.id ? `${type}_${raw.id}` : `${type}_${index}`,
                    type: type,
                    episodes: raw.episodes || (isScraperFormat
                        ? (raw.info?.match(/(\d+)\s*Episode/)?.[1] || '?')
                        : '?'),
                    year: raw.year || new Date().getFullYear(),
                    status: isScraperFormat
                        ? (type === 'aktuell' ? 'Laufend' : type === 'abgeschlossen' ? 'Abgeschlossen' : 'Geplant')
                        : (raw.status || 'Geplant'),
                    timeLabel: isScraperFormat
                        ? (type === 'kommend' ? 'Demnächst' : type === 'abgeschlossen' ? 'Abgeschlossen' : 'Aktuell')
                        : (type === 'kommend'
                            ? `In ${raw.dub_weeks || Math.floor(Math.random()*4)+1} Wochen`
                            : `Vor ${raw.days_ago || Math.floor(Math.random()*20)+1} Tagen`),
                    image: raw.image || '',
                    anisearchUrl: raw.url || '',
                };
            } catch (e) {
                console.error("Fehler beim Normalisieren der Anime-Daten:", e);
                renderGlobalError("Ein unerwarteter Fehler ist beim Verarbeiten der Anime-Daten aufgetreten. Bitte lade die Seite neu.");
                return {
                    id: `${type}_${index}`,
                    title: 'Fehlerhaftes Anime',
                    type: type,
                    format: 'Unbekannt',
                    episodes: '?',
                    year: new Date().getFullYear(),
                    status: 'Fehler',
                    timeLabel: 'Fehler',
                    image: '',
                    anisearchUrl: ''
                };
            }
        }

        // ─── Datenladen & Initialisierung ─────────────────────────────

        function applyDataToState(data, source) {
            try {
                const kommendeData      = data.kommende      || [];
                const aktuelleData      = data.aktuelle      || [];
                const abgeschlossenData = data.abgeschlossen || [];

                const allAnimes = [
                    ...kommendeData.map((a, i)      => normalizeAnime(a, i, 'kommend')),
                    ...aktuelleData.map((a, i)      => normalizeAnime(a, i, 'aktuell')),
                    ...abgeschlossenData.map((a, i) => normalizeAnime(a, i, 'abgeschlossen')),
                ];

                const prevSource = state.dataSource;
                state.animes     = allAnimes;
                state.dataSource = source;
                state.lastUpdate = new Date().toLocaleString('de-DE');
                state.hasAbgeschlossen = abgeschlossenData.length > 0;

                // Dynamisch Jahr und Format Dropdowns befüllen
                const yearSelect = document.getElementById('yearSelect');
                const formatSelect = document.getElementById('formatSelect');
                if (yearSelect && formatSelect && allAnimes.length > 0) {
                    const years = [...new Set(allAnimes.map(a => a.year).filter(y => y > 0))].sort((a,b) => b - a);
                    const formats = [...new Set(allAnimes.map(a => a.format).filter(Boolean))].sort();

                    let savedYear = null;
                    let savedFormat = null;
                    try {
                        savedYear = localStorage.getItem('premiumYear');
                        savedFormat = localStorage.getItem('premiumFormat');
                    } catch (e) {
                        // Ignore
                    }

                    const currYear = savedYear !== null ? savedYear : yearSelect.value;
                    const currFormat = savedFormat !== null ? savedFormat : formatSelect.value;

                    yearSelect.innerHTML = '<option value="all">Alle Jahre</option>' +
                        years.map(y => `<option value="${y}">${y}</option>`).join('');
                    formatSelect.innerHTML = '<option value="all">Alle Formate</option>' +
                        formats.map(f => `<option value="${f}">${f}</option>`).join('');

                    if (currYear === 'all' || years.includes(parseInt(currYear))) yearSelect.value = currYear;
                    if (currFormat === 'all' || formats.includes(currFormat)) formatSelect.value = currFormat;
                }

                // Zeige/Verstecke Abgeschlossen-Tab
                const tabAbs = document.getElementById('tabAbgeschlossen');
                if (tabAbs) tabAbs.style.display = state.hasAbgeschlossen ? '' : 'none';

                applyFilters();
                updateStats();
                updateApiStatus();
                updateOfflineBanner();

                if (prevSource !== source) {
                    const ts = data.timestamp
                        ? new Date(data.timestamp).toLocaleString('de-DE')
                        : '';
                    const msgs = {
                        live:   `🌐 Live-Daten: ${kommendeData.length} geplant · ${aktuelleData.length} aktuell · ${abgeschlossenData.length} abgeschl.`,
                        github: `🐙 GitHub Actions Daten (${ts}): ${allAnimes.length} Anime`,
                        cache:  `💾 Gecachte Daten: ${allAnimes.length} Anime (Starte Server für Live-Daten)`,
                        demo:   `✨ Demo-Modus – ${allAnimes.length} Animes`
                    };
                    addLog(msgs[source] || '');
                    if (source === 'live' && prevSource !== 'live') {
                        showNotification('🔴 Live-Daten von anisearch.de geladen! 🎉');
                    }
                }

                if (data.scraping) {
                    document.getElementById('scrapingIndicator')?.classList.add('visible');
                } else {
                    document.getElementById('scrapingIndicator')?.classList.remove('visible');
                }
            } catch (err) {
                renderGlobalError(err.message || 'Ein Fehler ist bei applyDataToState aufgetreten.');
            }
        }

        async function initializeAnimes() {
            try {
                addLog('📡 Verbinde mit Server...');

                // Quelle 1: Live-Server
                const serverData = await loadFromServer();
                if (serverData && (serverData.kommende || serverData.aktuelle)) {
                    applyDataToState(serverData, 'live');
                    startPolling();
                    return;
                }

                // Quelle 2: Gecachte JSON-Datei
                addLog('⚠️ Server nicht verfügbar – versuche gecachte Daten...');
                const cachedData = await loadFromCachedJson();
                if (cachedData && (cachedData.kommende || cachedData.aktuelle)) {
                    const age = cachedData.timestamp
                        ? new Date(cachedData.timestamp).toLocaleString('de-DE')
                        : 'unbekannt';
                    addLog(`💾 Gecachte Daten geladen (Stand: ${age})`);
                    applyDataToState(cachedData, 'cache');
                    startPolling();  // Im Hintergrund auf Server warten
                    return;
                }

                // Quelle 3: Demo-Daten
                addLog('✨ Kein Server & kein Cache – nutze Demo-Datenbank');
                applyDataToState({
                    kommende:      KOMMENDE_DUBS,
                    aktuelle:      AKTUELLE_DUBS,
                    abgeschlossen: []
                }, 'demo');
                startPolling();  // Auf Server warten
            } catch (err) {
                renderGlobalError(err.message || 'Kritischer Fehler bei der Initialisierung.');
            }
        }

        // ─── Auto-Polling ─────────────────────────────────────────────

        function startPolling() {
            if (state.pollTimer) return;
            state.pollTimer = setInterval(async () => {
                try {
                    const prev = state.dataSource;
                    const serverData = await loadFromServer();
                    if (serverData && (serverData.kommende || serverData.aktuelle)) {
                        if (prev !== 'live' || serverData.scraping !== undefined) {
                            applyDataToState(serverData, 'live');
                        }
                    } else if (prev === 'live') {
                        // Server weg – zurück auf Cache oder Demo
                        addLog('⚠️ Server-Verbindung verloren – Auto-Reconnect aktiv...');
                        const cached = await loadFromCachedJson();
                        if (cached) applyDataToState(cached, 'cache');
                        else applyDataToState({ kommende: KOMMENDE_DUBS, aktuelle: AKTUELLE_DUBS, abgeschlossen: [] }, 'demo');
                    }
                } catch (error) {
                    console.error('Fehler beim Auto-Polling:', error);
                    addLog('❌ Fehler beim Aktualisieren der Daten im Hintergrund.');
                }
            }, CONFIG.POLL_INTERVAL_MS);
        }

        async function manualRefresh() {
            try {
                addLog('🔄 Manueller Refresh...');
                // Trigger Server-Scrape falls vorhanden
                try {
                    const response = await fetchWithTimeout(CONFIG.REFRESH_ENDPOINT, 3000);
                    if (!response.ok) {
                        throw new Error(`HTTP Error: ${response.status}`);
                    }
                    addLog('⚙️ Scraper gestartet – Daten kommen in Kürze...');
                    document.getElementById('scrapingIndicator')?.classList.add('visible');
                } catch(e) {
                    /* kein Server */
                    showNotification('Fehler beim manuellen Refresh');
                }
                await initializeAnimes();
            } catch (error) {
                console.error("Fehler beim manuellen Refresh", error);
                renderGlobalError("Ein unerwarteter Fehler ist beim manuellen Refresh aufgetreten: " + (error.message || 'Unbekannt'));
            }
        }

        function updateStats() {
            try {
                const statsGrid = document.getElementById('statsGrid');
                if (!statsGrid) return;
                const kommendeCount      = state.animes.filter(a => a.type === 'kommend').length;
                const aktuelleCount      = state.animes.filter(a => a.type === 'aktuell').length;
                const abgeschlossenCount = state.animes.filter(a => a.type === 'abgeschlossen').length;
                const abgeschlossenCard  = abgeschlossenCount > 0 ? `
                    <div class="stat-card">
                        <div class="stat-value" style="background:linear-gradient(135deg,#86efac,#22c55e);-webkit-background-clip:text;">${abgeschlossenCount}</div>
                        <div class="stat-label">Abgeschlossen</div>
                    </div>` : '';
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${state.animes.length}</div>
                        <div class="stat-label">Gesamt Animes</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value glow-primary">${kommendeCount}</div>
                        <div class="stat-label">Bald verfügbar</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value glow-secondary">${aktuelleCount}</div>
                        <div class="stat-label">Kürzlich erschienen</div>
                    </div>
                    ${abgeschlossenCard}
                    <div class="stat-card">
                        <div class="stat-value">${state.watchlist.length}</div>
                        <div class="stat-label">In Watchlist</div>
                    </div>
                `;
            } catch (error) {
                renderGlobalError(error.message || 'Fehler beim Aktualisieren der Statistiken.');
            }
        }

        function applyFilters() {
            try {
                const searchInput = document.getElementById('searchInput');
                const searchTerm  = (searchInput?.value || '').toLowerCase();
                const sortVal     = document.getElementById('sortSelect').value;
                const selectedYear = document.getElementById('yearSelect')?.value || 'all';
                const selectedFormat = document.getElementById('formatSelect')?.value || 'all';

                try {
                    localStorage.setItem('premiumSearchTerm', searchInput?.value || '');
                    localStorage.setItem('premiumSortVal', sortVal);
                    localStorage.setItem('premiumYear', selectedYear);
                    localStorage.setItem('premiumFormat', selectedFormat);
                    localStorage.setItem('premiumTab', state.currentTab);
                } catch (e) {
                    console.warn('LocalStorage nicht verfügbar', e);
                    showNotification('Fehler beim Speichern der Filter');
                }

                let result = state.animes.filter(anime => {
                    const title        = (anime.title || '').toLowerCase();
                    const matchesSearch = !searchTerm || title.includes(searchTerm);
                    let matchesTab = true;

                    if (state.currentTab === 'kommende-dubs')       matchesTab = anime.type === 'kommend';
                    else if (state.currentTab === 'aktuelle-dubs')  matchesTab = anime.type === 'aktuell';
                    else if (state.currentTab === 'abgeschlossene-dubs') matchesTab = anime.type === 'abgeschlossen';
                    else if (state.currentTab === 'watchlist')      matchesTab = state.watchlist.some(w => w.id === anime.id);

                    const matchesYear = selectedYear === 'all' || anime.year === parseInt(selectedYear);
                    const matchesFormat = selectedFormat === 'all' || anime.format === selectedFormat;

                    return matchesSearch && matchesTab && matchesYear && matchesFormat;
                });

                // Sorting
                result.sort((a, b) => {
                    switch (sortVal) {
                        case 'title_asc': return (a.title || '').localeCompare(b.title || '', 'de');
                        case 'title_desc': return (b.title || '').localeCompare(a.title || '', 'de');
                        case 'year_desc': return (b.year || 0) - (a.year || 0);
                        case 'year_asc': return (a.year || 0) - (b.year || 0);
                        default: return 0;
                    }
                });

                state.filteredAnimes = result;
                state.currentPage = 1;
                renderAnimes();
            } catch (err) {
                renderGlobalError(err.message || 'Ein Fehler ist beim Anwenden der Filter aufgetreten.');
            }
        }

        function renderAnimes() {
            const contentArea = document.getElementById('contentArea');
            if (!contentArea) return;

            try {
                if (state.filteredAnimes.length === 0) {
                    contentArea.innerHTML = `
                        <div style="text-align: center; padding: 60px 20px; opacity: 0.7;">
                            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="margin-bottom: 20px;">
                                <circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line>
                            </svg>
                            <h2 style="font-family: var(--font-display);">Keine Animes gefunden</h2>
                            <p>Versuche einen anderen Suchbegriff oder Tab.</p>
                        </div>`;
                    document.getElementById('pagination').innerHTML = '';
                    return;
                }

                const start = (state.currentPage - 1) * state.pageSize;
                const end = start + state.pageSize;
                const paginated = state.filteredAnimes.slice(start, end);
                const totalPages = Math.ceil(state.filteredAnimes.length / state.pageSize);

                const html = paginated.map(anime => {
                    const isWatchlisted = state.watchlist.some(w => w.id === anime.id);
                    const isCurrent = anime.type === 'aktuell';

                    const isAbgeschlossen = anime.type === 'abgeschlossen';
                    const tagClass = isCurrent ? 'tag-aktuell' : isAbgeschlossen ? '' : 'tag-kommend';
                    const tagText  = isCurrent ? '🔥 Kürzlich' : isAbgeschlossen ? '✅ Abgeschlossen' : '⏱️ Bald';
                    const highLightClass = isCurrent ? 'recent' : 'soon';
                    const tagStyle = isAbgeschlossen ? 'background:rgba(34,197,94,0.8);color:#fff;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.2);display:inline-flex;align-items:center;gap:4px;' : '';

                    // Use real cover image from anisearch CDN, fallback to gradient bg
                    const imgHtml = anime.image
                        ? `<img src="${anime.image}" alt="${anime.title}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1;border-radius:12px 12px 0 0;" onerror="this.style.display='none'" />`
                        : getAbstractBg(anime.id);

                    // Note: Escaping title to avoid tooltip breaking
                    const tooltipText = `Titel: ${anime.title.replace(/"/g, '&quot;')}&#10;Jahr: ${anime.year}&#10;Format: ${anime.format}&#10;Episoden: ${anime.episodes}&#10;Status: ${anime.status}`;
                    return `
                        <div class="anime-card" onclick="openModal('${anime.id}')" onmouseenter="showTooltip(event, '${anime.id}')" onmouseleave="hideTooltip()" onmousemove="moveTooltip(event)" title="${anime.title} (${anime.year} | ${anime.type} | ${anime.episodes} Episoden)"
                             data-title="${anime.title ? anime.title.replace(/"/g, '&quot;') : ''}"
                             data-format="${anime.format || ''}"
                             data-episodes="${anime.episodes || ''}"
                             data-status="${anime.info || anime.status || ''}"
                             data-year="${anime.year || ''}">
                            <div class="anime-image">
                                ${imgHtml}
                                <div class="floating-tags">
                                    ${isAbgeschlossen
                                        ? `<span style="${tagStyle}">${tagText}</span>`
                                        : `<span class="tag-status ${tagClass}">${tagText}</span>`
                                    }
                                    <span class="episodes-badge">${anime.episodes} EP</span>
                                </div>
                            </div>
                            <div class="anime-content">
                                <div class="anime-title">${anime.title}</div>
                                <div class="anime-meta">
                                    <span>📅 ${anime.year}</span> • <span>📺 ${anime.format}</span>
                                </div>
                                <div class="anime-meta" style="margin-top:-6px;">
                                    <span>${anime.type === 'aktuell' ? anime.info || 'Laufend' : anime.info || 'Geplant'}</span>
                                </div>

                                <div class="time-highlight ${isAbgeschlossen ? 'recent' : highLightClass}">
                                    ${isCurrent ? '🟢 Synchronisation verfügbar' : isAbgeschlossen ? '✅ Deutsche Synchro abgeschlossen' : '⏳ Bald verfügbar'}
                                </div>

                                <div class="anime-actions">
                                    <button onclick="event.stopPropagation(); toggleWatchlist('${anime.id}', '${anime.title}');" class="${isWatchlisted ? 'active' : ''}">
                                        ${isWatchlisted ? '✓ In Watchlist' : '+ Watchlist'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');

                contentArea.innerHTML = `<div class="anime-grid">${html}</div>`;

                // Pagination
                let paginationHtml = '';
                // limit visible pages for huge lists
                const maxPages = Math.min(totalPages, 7);
                for (let i = 1; i <= maxPages; i++) {
                    paginationHtml += `<button onclick="goToPage(${i})" class="${i === state.currentPage ? 'active' : ''}">${i}</button>`;
                }
                if (totalPages > maxPages) paginationHtml += `<button disabled>...</button><button onclick="goToPage(${totalPages})">${totalPages}</button>`;

                document.getElementById('pagination').innerHTML = totalPages > 1 ? paginationHtml : '';
            } catch (error) {
                renderGlobalError(error.message || 'Beim Laden der Anime-Liste ist leider ein Fehler aufgetreten.');
            }
        }

        // Just a helper to generate unique looking abstract backgrounds for images since we don't have URLs
        function getAbstractBg(id) {
            const num = Array.from(id).reduce((acc, char) => acc + char.charCodeAt(0), 0);
            const hue = num % 360;
            const hue2 = (hue + 60) % 360;
            return `<div style="position: absolute; inset:0; background: linear-gradient(135deg, hsl(${hue}, 70%, 20%), hsl(${hue2}, 60%, 15%)); z-index:1;"></div>`;
        }

        function toggleWatchlist(id, title) {
            try {
                const idx = state.watchlist.findIndex(w => w.id === id);
                if (idx > -1) {
                    state.watchlist.splice(idx, 1);
                    showNotification(`Entfernt: ${title}`);
                } else {
                    state.watchlist.push({ id, title });
                    showNotification(`Gemerkt: ${title}`);
                }
                try {
                    localStorage.setItem('premiumWatchlist', JSON.stringify(state.watchlist));
                } catch (e) {
                    console.warn('LocalStorage nicht verfügbar', e);
                    showNotification('Fehler beim Speichern der Watchlist');
                }
                if (state.currentTab === 'watchlist') applyFilters(); // refresh if inside watchlist tab
                updateStats();

                const btn = event.currentTarget;
                if (idx > -1) {
                    btn.classList.remove('active');
                    btn.innerHTML = '+ Watchlist';
                } else {
                    btn.classList.add('active');
                    btn.innerHTML = '✓ In Watchlist';
                }
            } catch (error) {
                renderGlobalError(error.message || 'Fehler beim Aktualisieren der Watchlist.');
            }
        }

        function openModal(id) {
            try {
                const anime = state.animes.find(a => a.id === id);
                if (!anime) return;

                const isWatchlisted = state.watchlist.some(w => w.id === id);
                const isCurrent = anime.type === 'aktuell';
                const hlClass = isCurrent ? 'time-highlight recent' : 'time-highlight soon';

                const modalBody = document.getElementById('modalBody');
                const coverImg = anime.image
                    ? `<img src="${anime.image}" alt="${anime.title}" style="width:100%;max-height:220px;object-fit:cover;border-radius:12px;margin-bottom:20px;" onerror="this.style.display='none'" />`
                    : '';
                const anisearchLink = anime.anisearchUrl
                    ? `<a href="${anime.anisearchUrl}" target="_blank" rel="noopener" class="btn btn-glass" style="text-decoration:none;">🔗 Auf AniSearch</a>`
                    : '';
                modalBody.innerHTML = `
                    ${coverImg}
                    <h2 style="font-family: var(--font-display); font-size: 24px; margin-bottom: 8px;">${anime.title}</h2>
                    <div style="color: var(--text-muted); margin-bottom: 24px;">Release: ${anime.year} | ${anime.info || anime.status}</div>

                    <div class="${hlClass}" style="margin-bottom: 30px; padding: 16px; font-size: 15px;">
                        <strong>${isCurrent ? '🟢 Deutsche Synchronisation verfügbar' : '⏳ Deutsche Synchronisation geplant'}</strong>
                        <br/><small style="opacity:0.8;">Quelle: anisearch.de (Automatisch aktualisiert)</small>
                    </div>

                    <p style="color: var(--text-muted); line-height: 1.6; margin-bottom: 30px;">
                        Synchronisations-Daten werden automatisch von anisearch.de abgerufen und regelmäßig aktualisiert.
                    </p>

                    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                        <button class="btn btn-primary" style="flex: 1; justify-content: center;" onclick="toggleWatchlist('${id}', '${anime.title}'); closeModal();">
                            ${isWatchlisted ? 'Aus Watchlist entfernen' : 'Zur Watchlist hinzufügen'}
                        </button>
                        ${anisearchLink}
                        <button class="btn btn-glass" onclick="closeModal()">Schließen</button>
                    </div>
                `;
                document.getElementById('detailsModal').classList.add('active');
            } catch (error) {
                renderGlobalError(error.message || 'Es gab ein Problem beim Öffnen der Anime-Details.');
            }
        }

        function closeModal() {
            document.getElementById('detailsModal').classList.remove('active');
        }

        let tooltipHideTimeout;

        function showTooltip(event, id) {
            try {
                clearTimeout(tooltipHideTimeout);
                const anime = state.animes.find(a => a.id === id);
                if (!anime) return;

                const tooltip = document.getElementById('globalTooltip');
                if (!tooltip) return;

                let infoHtml = `<h4>${anime.title}</h4>`;
                infoHtml += `<div class="global-tooltip-row"><span class="global-tooltip-label">Typ:</span> <span>${anime.format || 'Unbekannt'}</span></div>`;
                infoHtml += `<div class="global-tooltip-row"><span class="global-tooltip-label">Jahr:</span> <span>${anime.year || 'Unbekannt'}</span></div>`;
                infoHtml += `<div class="global-tooltip-row"><span class="global-tooltip-label">Episoden:</span> <span>${anime.episodes || '?'}</span></div>`;
                infoHtml += `<div class="global-tooltip-row"><span class="global-tooltip-label">Status:</span> <span>${anime.status || 'Unbekannt'}</span></div>`;

                if (anime.info) {
                    infoHtml += `<div style="margin-top: 8px; font-size: 11px; opacity: 0.8; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px;">${anime.info}</div>`;
                }

                tooltip.innerHTML = infoHtml;
                tooltip.style.display = 'block';

                // force reflow before opacity
                void tooltip.offsetWidth;
                tooltip.classList.add('visible');

                moveTooltip(event);
            } catch (error) {
                showNotification("Ein Fehler ist beim Anzeigen des Tooltips aufgetreten."); console.error("Fehler beim Anzeigen des Tooltips:", error);
            }
        }

        function hideTooltip() {
            const tooltip = document.getElementById('globalTooltip');
            if (!tooltip) return;
            tooltip.classList.remove('visible');
            // wait for transition before display:none
            tooltipHideTimeout = setTimeout(() => {
                tooltip.style.display = 'none';
            }, 200);
        }

        function moveTooltip(event) {
            try {
                const tooltip = document.getElementById('globalTooltip');
                if (!tooltip || tooltip.style.display === 'none') return;

                const tooltipRect = tooltip.getBoundingClientRect();
                const margin = 15;

                let top = event.clientY + 20;
                let left = event.clientX + 20;

                // Check boundaries
                if (left + tooltipRect.width > window.innerWidth - margin) {
                    left = event.clientX - tooltipRect.width - 20;
                }

                if (top + tooltipRect.height > window.innerHeight - margin) {
                    top = event.clientY - tooltipRect.height - 20;
                }

                tooltip.style.top = top + 'px';
                tooltip.style.left = left + 'px';
            } catch (error) {
                console.error("Fehler beim Bewegen des Tooltips:", error);
            }
        }

        function goToPage(page) {
            try {
                state.currentPage = page;
                renderAnimes();
                window.scrollTo({ top: document.querySelector('.dashboard-panel').offsetTop - 100, behavior: 'smooth' });
            } catch (error) {
                console.error("Fehler bei der Pagination:", error);
                renderGlobalError("Ein Fehler ist beim Seitenwechsel aufgetreten.");
            }
        }

        function updateApiStatus() {
            try {
                const statusEl = document.getElementById('apiStatus');
                if (!statusEl) return;
                const configs = {
                    live:   { cls: 'online',  dot: '#34d399', label: 'Live · anisearch.de' },
                    github: { cls: 'cached',  dot: '#60a5fa', label: '🐙 GitHub Actions' },
                    cache:  { cls: 'cached',  dot: '#fbbf24', label: 'Gecachte Daten' },
                    demo:   { cls: 'offline', dot: '#f87171', label: 'Demo-Modus' },
                    none:   { cls: 'loading', dot: '#93c5fd', label: 'Verbinde...' },
                };
                const cfg = configs[state.dataSource] || configs.none;
                statusEl.className = 'api-status ' + cfg.cls;
                statusEl.innerHTML = `<span style="display:inline-block;width:8px;height:8px;background:${cfg.dot};border-radius:50%"></span> ${cfg.label}`;
            } catch (error) {
                showNotification("Ein Fehler ist beim Aktualisieren des API-Status aufgetreten."); console.error("Fehler beim Aktualisieren des API-Status:", error);
            }
        }

        function updateOfflineBanner() {
            try {
                const banner = document.getElementById('offlineBanner');
                if (!banner) return;
                if (state.dataSource === 'demo') {
                    banner.classList.add('visible');
                } else {
                    banner.classList.remove('visible');
                }
            } catch (error) {
                showNotification("Ein Fehler ist beim Aktualisieren des Banners aufgetreten."); console.error("Fehler beim Aktualisieren des Offline-Banners:", error);
            }
        }

        function showNotification(message) {
            try {
                const container = document.getElementById('notification');
                if (!container) return;
                const notif = document.createElement('div');
                notif.className = `notification`;
                notif.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    ${message}
                `;
                container.appendChild(notif);
                setTimeout(() => {
                    notif.style.opacity = '0';
                    notif.style.transform = 'translateY(20px)';
                    setTimeout(() => notif.remove(), 300);
                }, 4000);
            } catch (error) {
                renderGlobalError("Ein kritischer Fehler ist bei der Benachrichtigung aufgetreten."); console.error("Fehler bei der Anzeige der Benachrichtigung:", error);
            }
        }

        function updateTabs() {
            try {
                document.querySelectorAll('.tab-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.dataset.tab === state.currentTab) {
                        btn.classList.add('active');
                    }
                });
            } catch (error) {
                showNotification("Ein Fehler ist beim Aktualisieren der Tabs aufgetreten."); console.error("Fehler beim Aktualisieren der Tabs:", error);
            }
        }

        // Globale Fehlerbehandlung für unvorhergesehene Abstürze
        function renderGlobalError(errorMsg) {
            const contentArea = document.getElementById('contentArea');
            if (!contentArea) return;

            contentArea.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; opacity: 0.9;">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="1" style="margin-bottom: 20px;">
                        <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <h2 style="font-family: var(--font-display); color: #ef4444; margin-bottom: 12px;">Hoppla, ein unerwarteter Fehler ist aufgetreten!</h2>
                    <p style="color: var(--text-muted); margin-bottom: 20px;">Die Anwendung konnte leider nicht weiter ausgeführt werden. Bitte lade die Seite neu.</p>
                    <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 20px;">Details: ${errorMsg}</p>
                    <button class="btn btn-primary" style="margin: 0 auto; display: inline-flex;" onclick="location.reload()">
                        🔄 Seite neu laden
                    </button>
                </div>`;
            document.getElementById('pagination').innerHTML = '';
        }

        window.addEventListener('error', (event) => {
            console.error('Ungefangener Fehler:', event.error || event.message);
            renderGlobalError(event.message || 'Unbekannter Fehler');
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unbehandeltes Promise Reject:', event.reason);
            renderGlobalError(event.reason?.message || 'Unbekannter Fehler bei Netzwerk/API');
        });

        document.addEventListener('DOMContentLoaded', () => {
            try {
                try {
                    const saved = localStorage.getItem('premiumWatchlist');
                    try {
                        state.watchlist = saved ? JSON.parse(saved) : [];
                    } catch (parseError) {
                        console.error('Fehler beim Parsen der Watchlist:', parseError);
                        state.watchlist = [];
                        renderGlobalError('Fehler beim Laden der Watchlist (Daten beschädigt)');
                    }
                } catch (e) {
                    console.warn('LocalStorage Watchlist Fehler', e);
                    showNotification('Fehler beim Laden der Watchlist');
                    state.watchlist = [];
                }

                try {
                    const savedSearchTerm = localStorage.getItem('premiumSearchTerm');
                    if (savedSearchTerm !== null) {
                        const searchInput = document.getElementById('searchInput');
                        if (searchInput) searchInput.value = savedSearchTerm;
                    }
                } catch (e) {
                    console.warn('LocalStorage Suchbegriff Fehler', e);
                }

                try {
                    const savedSortVal = localStorage.getItem('premiumSortVal');
                    if (savedSortVal !== null) {
                        const sortSelect = document.getElementById('sortSelect');
                        if (sortSelect) sortSelect.value = savedSortVal;
                    }
                } catch (e) {
                    console.warn('LocalStorage Sortierung Fehler', e);
                }

            try {
                const savedTab = localStorage.getItem('premiumTab');
                if (savedTab !== null) {
                    state.currentTab = savedTab;
                    updateTabs();
                }
            } catch (e) {
                console.warn('LocalStorage Tab Fehler', e);
            }

            try {
                const savedPageSize = localStorage.getItem('premiumPageSize');
                if (savedPageSize !== null) {
                    const pageSizeSelect = document.getElementById('pageSizeSelect');
                    if (pageSizeSelect) pageSizeSelect.value = savedPageSize;
                }
            } catch (e) {
                console.warn('LocalStorage Seitengröße Fehler', e);
            }

            // Keyboard Shortcuts
            document.addEventListener('keydown', (e) => {
                // Ignore if user is typing in an input or select
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
                    if (e.key === 'Escape') {
                        e.target.blur();
                    }
                    return;
                }

                if (e.key === '/') {
                    e.preventDefault();
                    const searchInput = document.getElementById('searchInput');
                    if (searchInput) {
                        searchInput.focus();
                        searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                } else if (e.key === 'Escape') {
                    closeModal();
                }
            });

            document.getElementById('searchInput').addEventListener('input', applyFilters);
            document.getElementById('sortSelect').addEventListener('change', applyFilters);
            document.getElementById('yearSelect').addEventListener('change', applyFilters);
            document.getElementById('formatSelect').addEventListener('change', applyFilters);
            document.getElementById('pageSizeSelect').addEventListener('change', (e) => {
                state.pageSize = parseInt(e.target.value) || 24;
                try {
                    localStorage.setItem('premiumPageSize', state.pageSize);
                } catch (err) {
                    console.warn('LocalStorage nicht verfügbar', err);
                    showNotification('Fehler beim Speichern der Seitengröße');
                }
                applyFilters();
            });

            // Tooltip Logic
            const tooltip = document.getElementById('animeTooltip');
            let currentCard = null;

            document.body.addEventListener('mouseover', (e) => {
                const card = e.target.closest('.anime-card');
                if (card && currentCard !== card) {
                    currentCard = card;
                    const title = card.dataset.title || 'Unbekannt';
                    const format = card.dataset.format || '?';
                    const episodes = card.dataset.episodes || '?';
                    const status = card.dataset.status || '?';
                    const year = card.dataset.year || '?';

                    tooltip.innerHTML = `
                        <h3>${title}</h3>
                        <div class="tooltip-detail"><span>📺</span> Format: ${format}</div>
                        <div class="tooltip-detail"><span>🎬</span> Episoden: ${episodes}</div>
                        <div class="tooltip-detail"><span>📅</span> Jahr: ${year}</div>
                        <div class="tooltip-detail"><span>ℹ️</span> Status: ${status}</div>
                    `;
                    tooltip.style.opacity = '1';
                }
            });

            document.body.addEventListener('mousemove', (e) => {
                if (currentCard && tooltip.style.opacity === '1') {
                    const offset = 15;
                    let left = e.clientX + offset;
                    let top = e.clientY + offset;

                    const rect = tooltip.getBoundingClientRect();
                    if (left + rect.width > window.innerWidth) {
                        left = e.clientX - rect.width - offset;
                    }
                    if (top + rect.height > window.innerHeight) {
                        top = e.clientY - rect.height - offset;
                    }

                    tooltip.style.left = `${left}px`;
                    tooltip.style.top = `${top}px`;
                }
            });

            document.body.addEventListener('mouseout', (e) => {
                const card = e.target.closest('.anime-card');
                if (card && !card.contains(e.relatedTarget)) {
                    currentCard = null;
                    tooltip.style.opacity = '0';
                }
            });

            document.getElementById('refreshBtn').addEventListener('click', () => {
                addLog('🔄 Manueller Resync...');
                manualRefresh();
            });
            document.getElementById('closeModalBtn').addEventListener('click', closeModal);

            document.getElementById('watchlistBtn').addEventListener('click', () => {
                state.currentTab = 'watchlist';
                updateTabs();
                applyFilters();
            });

            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    state.currentTab = btn.dataset.tab || 'alle';
                    updateTabs();
                    applyFilters();
                });
            });

            initializeAnimes();
            setTimeout(() => { showNotification('Datenbank geladen & bereit 🚀'); }, 800);
            } catch (err) {
                console.error("Unerwarteter Fehler bei der Initialisierung:", err);
                renderGlobalError(err.message || 'Fehler beim Laden der Seite.');
            }
        });
