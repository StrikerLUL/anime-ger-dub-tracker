#!/bin/bash
# Replace showGlobalError with renderGlobalError globally
sed -i 's/showGlobalError(/renderGlobalError(/g' "Anime Synchro Tracker v11.0.1.html"

# Remove the showGlobalError function body
# It starts at 'function renderGlobalError(errorMsg)' around line 1014-ish since we already renamed it
