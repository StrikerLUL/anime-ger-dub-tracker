import re

with open('Anime Synchro Tracker v11.0.1.html', 'r', encoding='utf-8') as f:
    text = f.read()

# I want to add try/catch in:
# showGlobalError
# formatTime (no API or DOM that fails easily, maybe not needed, but can add)
# getAbstractBg
# closeModal
# hideTooltip
# renderGlobalError

def add_try_catch(func_name, text):
    pattern = r'(function\s+' + func_name + r'\s*\([^)]*\)\s*\{)(?!\s*try\s*\{)'

    # We find where it starts
    match = re.search(pattern, text)
    if not match:
        return text

    start = match.end()

    # We need to find the matching closing brace
    brace_count = 1
    i = start
    while i < len(text) and brace_count > 0:
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
        i += 1

    # i is now right after the closing brace

    body = text[start:i-1]

    # Indent body
    body_lines = body.split('\n')
    indented_body = '\n'.join(['    ' + line if line.strip() else line for line in body_lines])

    new_func = match.group(1) + "\n            try {" + indented_body + "            } catch (error) {\n                console.error(\"Error in " + func_name + ":\", error);\n            }\n        }"

    return text[:match.start()] + new_func + text[i:]


for func in ['showGlobalError', 'formatTime', 'getAbstractBg', 'closeModal', 'hideTooltip', 'renderGlobalError']:
    text = add_try_catch(func, text)

with open('Anime Synchro Tracker v11.0.1.html_new', 'w', encoding='utf-8') as f:
    f.write(text)
