import re
with open("Anime Synchro Tracker v11.0.1.html") as f:
    text = f.read()

text = text.replace("""            } catch (err) {
                console.error("Fehler beim manuellen Refresh", err);
                showGlobalError("Ein unerwarteter Fehler ist beim Aktualisieren aufgetreten: " + (err.message || 'Unbekannt'));
            } catch (error) {
                showGlobalError("Ein unerwarteter Fehler ist beim manuellen Refresh aufgetreten: " + error.message);
            }""", """            } catch (err) {
                console.error("Fehler beim manuellen Refresh", err);
                showGlobalError("Ein unerwarteter Fehler ist beim Aktualisieren aufgetreten: " + (err.message || 'Unbekannt'));
            }""")

with open("Anime Synchro Tracker v11.0.1.html", "w") as f:
    f.write(text)
