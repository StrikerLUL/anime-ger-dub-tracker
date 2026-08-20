with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()

import re

# We can search for localStorage
matches = re.finditer(r'localStorage', text)
for m in matches:
    idx = m.start()
    line = text.count('\n', 0, idx) + 1
    # print the context around it
    print(f"Line {line}: {text[idx-50:idx+50]}")
