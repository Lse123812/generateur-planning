#!/usr/bin/env python3
"""Lance La Bonne Frite en local, sans base de données ni service cloud."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
import webbrowser

DOSSIER = Path(__file__).resolve().parent
PORT = 8000

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOSSIER), **kwargs)

if __name__ == "__main__":
    os.chdir(DOSSIER)
    url = f"http://127.0.0.1:{PORT}/index.html"
    print("La Bonne Frite est disponible à :", url)
    print("Pour arrêter le serveur : Ctrl+C")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
