with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()
import re
match = re.search(r'function applyFilters\(\) \{([\s\S]*?)function renderAnimes\(\) \{', text)
if match:
    print(match.group(0))
