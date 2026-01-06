# 🎬 Anime Synchro Tracker v9.0

Track German dubbed anime releases with automatic synchronization detection. Discover upcoming dubs, manage your watchlist, and stay updated on your favorite series.

## ✨ Features

- **🎯 Automatic Dub Detection** - Automatically tracks German dubbed anime releases from multiple sources
- **📌 Watchlist Management** - Save your favorite anime and sync across sessions
- **🔍 Advanced Filters** - Search, sort by rating/year/title, filter by content rating
- **⚠️ 18+ Content Toggle** - Show/hide mature content based on preferences
- **📊 Live Statistics** - View total anime count, dubbed releases, and watchlist status
- **🌙 Dark/Light Mode** - Comfortable viewing in any lighting condition
- **📱 Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **⚡ Smart Caching** - Efficient data loading with smart fallback system
- **🔄 Auto-Update** - Periodic updates to keep dub information current
- **📑 Customizable Pagination** - Choose 24, 36, or 48 anime per page

## ⚠️ Status: Beta / In Development

**Important:** This project is still in **Beta Phase**. Not all features are working perfectly yet. Bugs and errors are possible.

### Known Issues
- ⚠️ API rate limits can cause errors
- ⚠️ Crunchyroll integration is not fully reliable
- ⚠️ Some anime images fail to load
- ⚠️ Synchronization data is incomplete for some titles

### Help Us Improve! 🤝
If you're interested in helping with development or reporting bugs, **please join our Discord community:**

**👉 https://discord.gg/WuPCK8fcVQ

On Discord you can:
- 🐛 Report bugs and crashes
- 💡 Request new features
- 🛠️ Help with development
- 💬 Chat with other users
- 📚 Provide feedback and suggestions

---

## 🚀 Getting Started

### Option 1: Direct Use (No Installation)
1. Download the HTML file
2. Open in any modern web browser
3. Start browsing and tracking anime!

### Option 2: Deploy to Web Server
```bash
# Copy the HTML file to your web server
cp anime-synchro-tracker.html /var/www/html/
# Access via: http://yourdomain.com/anime-synchro-tracker.html
```

### Option 3: Local Development
```bash
# Clone or download the repository
git clone https://github.com/StrikerLUL/anime-ger-dub-tracker.git
cd anime-synchro-tracker

# Serve locally (requires Python or Node.js)
python -m http.server 8000
# Then open: http://localhost:8000
```

## 📖 How to Use

### Searching and Filtering
1. **Search** - Type anime name in the search box
2. **Sort** - Choose sorting option (rating, year, title)
3. **Dub Status** - Filter by synchronization availability
4. **Rating** - Set minimum score threshold
5. **Content** - Show/hide 18+ content with the toggle

### Managing Your Watchlist
- Click the **"+"** button on any anime card to add to watchlist
- Access your watchlist from the **"📌 Watchlist"** tab
- Watchlist syncs automatically with browser storage

### Viewing Anime Details
1. Click on any anime card
2. View full details including:
   - English & Japanese titles
   - Genres and synopsis
   - Episode count and status
   - Dub release information
3. Add/remove from watchlist directly from the modal

### Tabs Explained
- **🌟 Alle** - Browse all available anime
- **🆕 Neue Dubs** - Filter for upcoming German releases
- **📌 Watchlist** - Your saved anime collection
- **🔧 Info** - System statistics and debug information

## 🔌 API Sources

The application integrates with multiple anime databases:

- **Jikan API** - Comprehensive anime data (top airing series, ratings, episodes)
- **AniList** - Trending anime and synchronization metadata
- **Crunchyroll** - German subtitle availability
- **Local Database** - Fallback dub dates for reliability

### Ratelimit Handling
- Automatic retry logic for API failures
- Smart exponential backoff for rate limits
- 3-second wait on HTTP 429 responses
- Fallback to cached/local data

## ⚙️ Settings

### Page Size
Choose how many anime to display per page:
- 24 anime (default - balanced)
- 36 anime (more content)
- 48 anime (maximum)

### Adult Content
Toggle display of 18+ anime (Ecchi, R-rated content):
- **OFF** - Family-friendly content only
- **ON** - Show all content including mature titles

### Sorting Options
- ⭐ **Best Rating** - Highest scores first
- **Lowest Rating** - Lowest scores first
- 📅 **Newest First** - Latest anime first
- **A-Z Title** - Alphabetical order

## 💾 Data Storage

The application uses browser localStorage for:
- **Watchlist** - Your saved anime (persists across sessions)
- **Page Size** - Your preferred pagination setting
- **18+ Preference** - Your content rating filter choice

All data is stored locally in your browser - no server upload.

## 🛠️ Technical Details

### Technology Stack
- **Frontend**: Vanilla JavaScript (ES6+)
- **Styling**: CSS3 with CSS Variables
- **APIs**: RESTful & GraphQL
- **Storage**: Browser localStorage

### Browser Compatibility
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

### Performance
- **Load Time**: ~10-15 seconds (including API calls)
- **Initial Anime Count**: 120-130 series
- **Database Size**: ~15 hardcoded fallback entries
- **Cache Duration**: 5 minutes

## 🐛 Troubleshooting

### "Keine Anime gefunden" (No Anime Found)
- **Solution**: Check internet connection, wait 1 minute, refresh page
- **Fallback**: Local database will load (15+ anime)

### High HTTP 429 Errors
- **Cause**: API rate limiting
- **Solution**: Wait 10 minutes, reduce page size, refresh page
- **Status**: Check 🔧 Info tab for error count

### Watchlist Not Saving
- **Cause**: Browser storage disabled or full
- **Solution**: Enable local storage in settings, clear old data
- **Workaround**: Use browser bookmark for favorites

### Images Not Loading
- **Cause**: Anime database image URL issues
- **Solution**: Refresh page, try different anime
- **Display**: Placeholder icon shows if image unavailable

### Still Having Problems? 🆘
If you have a problem not listed here:
1. Open the **Info tab (🔧)** and note the errors
2. Join our **Discord server** and describe the issue
3. Share your error messages with the community

## 📊 Statistics Dashboard

The Info tab (🔧) displays:
- **Anime** - Total anime count loaded
- **Mit Dub** - Count with German synchronization info
- **Watchlist** - Items in your watchlist
- **Seiten** - Pages loaded from API
- **Fehler** - Error count during session

## 🌍 Localization

- **Language**: German (Deutsch) - with English documentation
- **Date Format**: HH:MM:SS (24-hour)
- **API Locale**: de_DE for German content
- **UI Text**: All interface text in German

## 📝 License

This project is open source and available for personal and educational use.

## 🤝 Contributing

Found a bug or have a suggestion? **Please join our Discord community!**

### How You Can Help
- 🐛 **Bug Reports** - Report bugs and crashes
- 💡 **Feature Requests** - Suggest new features
- 🔧 **Code Contributions** - Help with programming
- 📝 **Documentation** - Improve documentation
- 🌍 **Translations** - Support multiple languages


## 📧 Support

For issues, questions, or feedback:
- **🎯 Primary**: Join our Discord server
- Create an issue on GitHub
- Check the Info tab (🔧) for technical details
- Clear browser cache if experiencing problems
- Read through existing GitHub issues first

## 🎯 Roadmap

- [ ] Multiple language support (English, French, Spanish, etc.)
- [ ] User accounts & cloud sync
- [ ] Push notifications for dub releases
- [ ] Advanced filtering (by studio, season, year)
- [ ] Social sharing features
- [ ] Desktop and mobile app versions
- [ ] More reliable Crunchyroll integration
- [ ] Community-submitted dub data
- [ ] Improved error handling and logging
- [ ] Performance optimization
- [ ] Dark mode theme improvements
- [ ] Advanced analytics and statistics

## 🙏 Acknowledgments

- **Jikan API** - Anime data provider
- **AniList** - Community anime database
- **Crunchyroll** - German subtitle information
- **All contributors** - For help and feedback
- **Community** - For testing and suggestions
- **Open Source Community** - For inspiration and tools

---

**Made with ❤️ for anime fans** | v9.0 (Beta) | 2026

**🚨 Status: In Active Development – Join Discord to help improve this project!**

---

## Quick Links

- 🎯 Discord Server  (https://discord.gg/WuPCK8fcVQ)
