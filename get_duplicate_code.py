import re

with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Lines 1858 to 1980
lines = text.split('\n')
for i, line in enumerate(lines[1858:1955]):
    print(f"{i + 1859}: {line}")
