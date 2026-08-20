import re
with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()

funcs = re.split(r'function\s+\w+\s*\(', text)
print("Total functions found:", len(funcs)-1)
