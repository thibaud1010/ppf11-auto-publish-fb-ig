"""Muestra QUE item elegiria cada idioma, sin tocar el estado (solo lectura).

Uso: python pick_preview.py [dias]
Simula N dias seguidos en memoria para ver si las paginas coinciden en la imagen.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys

from src.config import load_accounts
from src.content import load_items
from src import state as st

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
LANGS = ["es", "en", "fr", "de", "it", "pt", "nl"]


def short(u):
    return "/".join(u.split("/")[-2:])


def preview(platform, kind):
    accounts = load_accounts()["languages"]
    state = st.load_state()  # copia en memoria; NO se guarda
    print(f"\n=== {platform}:{kind} ===")
    for day in range(1, DAYS + 1):
        picks = {}
        used = set()
        for lang in LANGS:
            if not accounts.get(lang, {}).get("enabled", True):
                continue
            items = load_items(kind, lang)
            if hasattr(st, "order_for_language"):
                items = st.order_for_language(items, lang)
            key = f"{platform}:{lang}:{kind}"
            item = st.pick_next(items, key, state, exclude=used)
            if not item:
                continue
            picks[lang] = item["image_url"]
            used.add(item["image_url"])
            st.mark_posted(state, key, item["image_url"])  # solo en memoria
        distintas = len(set(picks.values()))
        flag = "OK" if distintas == len(picks) else f"!! {distintas} imagenes para {len(picks)} paginas"
        print(f"  dia {day}: {flag}")
        for lang, url in picks.items():
            print(f"     {lang}: {short(url)}")


if __name__ == "__main__":
    preview("fb", "exercises")
    preview("fb", "articles")
    preview("ig", "exercises")
