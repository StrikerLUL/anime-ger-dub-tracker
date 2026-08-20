function fixTryCatchInDOMContentLoaded() {
  const code = `
            try {
                // Parse localStorage with individual try-catch to avoid one bad value killing all settings
                try {
                    const saved = localStorage.getItem('premiumWatchlist');
                    state.watchlist = saved ? JSON.parse(saved) : [];
                } catch (e) {
                    console.warn('LocalStorage nicht verfügbar', e);
                    showNotification('Fehler beim Laden der Watchlist');
                    state.watchlist = [];
                const saved = localStorage.getItem('premiumWatchlist');
                try {
                    state.watchlist = saved ? JSON.parse(saved) : [];
                } catch (parseError) {
                    console.error('Fehler beim Parsen der Watchlist:', parseError);
                    state.watchlist = [];
                    showNotification('Fehler beim Laden der Watchlist');
                }
                    showGlobalError('Fehler beim Laden der Watchlist (Daten beschädigt)');
                    state.watchlist = [];
                }
                state.watchlist = saved ? JSON.parse(saved) : [];
            } catch (e) {
                console.warn('LocalStorage Watchlist Fehler', e);
                showNotification('Fehler beim Laden der Watchlist');
                state.watchlist = [];
            }
`;
  console.log(code);
}
fixTryCatchInDOMContentLoaded();
