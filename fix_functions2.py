import re
with open("Anime Synchro Tracker v11.0.1.html_new") as f:
    text = f.read()

# check formatTime
match = re.search(r'function\s+formatTime\s*\([^)]*\)\s*\{', text)
if match:
    # it was added correctly
    pass

# We should also ensure formatTime, addLog, getAbstractBg, closeModal, hideTooltip, showGlobalError, renderGlobalError, formatTime, addLog have proper try catch block and the syntax is correct.

# Wait, addLog has NO try catch
