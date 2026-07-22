"""Lectura del pool de contenido (CSV) y renderizado de captions."""
import csv
from collections import defaultdict

from .config import CONTENT_DIR

# columnas esperadas en los CSV: language,title,summary,url,image_url,hashtags


def load_items(kind, language):
    """kind = 'articles' | 'exercises'. Devuelve las filas del idioma dado."""
    path = CONTENT_DIR / f"{kind}.csv"
    items = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("language") or "").strip().lower() == language.lower():
                # normaliza espacios
                clean = {k: (v or "").strip() for k, v in row.items()}
                if clean.get("url") and clean.get("image_url"):
                    items.append(clean)
    return items


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render_caption(template, row):
    """Rellena la plantilla con las columnas de la fila. Claves ausentes se dejan tal cual."""
    return template.format_map(_SafeDict(row))
