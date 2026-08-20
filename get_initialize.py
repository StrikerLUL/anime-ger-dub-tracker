with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()

import re

match = re.search(r'async function initializeAnimes\(\) \{([\s\S]*?)function startPolling\(\) \{', text)
if match:
    print(match.group(1))
