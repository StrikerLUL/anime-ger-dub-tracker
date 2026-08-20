with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()

# Let's remove the try catch I added to addLog and getAbstractBg because they were inside other places or something?
# Actually, the issue is that I didn't verify the structure. Let's see what is inside applyDataToState.
