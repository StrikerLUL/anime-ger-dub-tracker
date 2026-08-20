import re

with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    text = f.read()

# I want to fix the malformed try-catch block inside DOMContentLoaded
# and remove the duplicated code
# The code around line 1858-1955 is completely messed up. I will rewrite it cleanly.

new_code = """        document.addEventListener('DOMContentLoaded', () => {
            try {
                // Parse localStorage with individual try-catch to avoid one bad value killing all settings
                try {
                    const saved = localStorage.getItem('premiumWatchlist');
                    if (saved) {
                        try {
                            state.watchlist = JSON.parse(saved);
                        } catch (parseError) {
                            console.error('Fehler beim Parsen der Watchlist:', parseError);
                            state.watchlist = [];
                            showNotification('Fehler beim Laden der Watchlist');
                        }
                    } else {
                        state.watchlist = [];
                    }
                } catch (e) {
                    console.warn('LocalStorage nicht verfügbar', e);
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
"""

text = re.sub(r'        document\.addEventListener\(\'DOMContentLoaded\', \(\) => \{\n(?:.|\n)*?            // Keyboard Shortcuts\n', new_code + '\n            // Keyboard Shortcuts\n', text)

with open('Anime Synchro Tracker v11.0.1.html_new', 'w', encoding='utf-8') as f:
    f.write(text)
