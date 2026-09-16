#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prüft anime_data.json, bevor sie veröffentlicht wird.

Identisch zu:  python -m tracker check

    python check_data.py [pfad/zur/anime_data.json]
"""

import sys

from tracker.check import check
from tracker.config import DATA_FILE

if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else DATA_FILE))
