import re

with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    text = f.read()

# find all 'function name('
matches = re.finditer(r'(async\s+)?function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{', text)
for m in matches:
    name = m.group(2)
    start = m.end()

    # find the closing brace
    brace_count = 1
    i = start
    while i < len(text) and brace_count > 0:
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
        i += 1

    func_body = text[start:i]
    if 'try' not in func_body:
        print(f"Function {name} has NO try block.")
    else:
        # print(f"Function {name} HAS try block.")
        pass
