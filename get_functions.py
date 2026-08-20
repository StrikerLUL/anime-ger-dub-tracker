import re

with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    content = f.read()

functions = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', content)
print("Functions found:")
for func in functions:
    print(func)
