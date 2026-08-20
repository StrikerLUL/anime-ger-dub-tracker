import re
with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

functions_status = []
for i, line in enumerate(lines):
    match = re.search(r'function\s+([a-zA-Z0-9_]+)\s*\(', line)
    if match:
        func_name = match.group(1)
        has_try = False
        # look forward next lines
        for j in range(i+1, min(i+5, len(lines))):
            if 'try {' in lines[j]:
                has_try = True
                break
        functions_status.append((func_name, has_try, i+1))

for func in functions_status:
    print(f"Function {func[0]} at line {func[2]} has try: {func[1]}")
