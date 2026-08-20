import re

with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'localStorage' in line or 'fetch' in line:
        # trace back to find the closest function
        for j in range(i, -1, -1):
            if 'function' in lines[j] or '=>' in lines[j]:
                print(f"Line {i+1} ('{line.strip()}') is inside:\n{lines[j].strip()} (Line {j+1})")
                break
        print("-" * 40)
