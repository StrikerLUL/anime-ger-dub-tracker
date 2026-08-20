with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()

# Wait, why did the tooltip test fail with "No anime cards found to test tooltip."?
# It means the anime cards didn't load.
# Let's check why they didn't load in playwrigth.
