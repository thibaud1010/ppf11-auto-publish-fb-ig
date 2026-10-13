#!/usr/bin/env python3
"""¿Que publicadores tienen algun idioma al que le toca AHORA? (src/schedule.py)

Lo usa .github/workflows/tick.yml para no instalar nada en los disparos en los
que no toca publicar. Solo libreria estandar. Escribe lineas clave=true|false
(formato de $GITHUB_OUTPUT): fb_article, fb_exercise, ig, reels, any.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.config import load_accounts  # noqa: E402
from src import schedule as sch  # noqa: E402

GROUPS = {
    "fb_article": (["fb:article"], "facebook"),
    "fb_exercise": (["fb:exercise"], "facebook"),
    "ig": (["ig:morning", "ig:evening"], "instagram"),
    "reels": (["reels"], "instagram"),
}
REELS_LANGS = ["es", "en", "de", "it", "pt", "nl"]   # fr es el idioma origen


def main():
    langs = load_accounts()["languages"]
    out = {}
    for name, (posts, platform) in GROUPS.items():
        out[name] = any(
            sch.due(lang, post)
            for lang, cfg in langs.items()
            if cfg.get("enabled", True) and cfg.get(platform)
            and (name != "reels" or lang in REELS_LANGS)
            for post in posts
        )
    out["any"] = any(out.values())
    for k, v in out.items():
        print(f"{k}={'true' if v else 'false'}")


if __name__ == "__main__":
    main()
