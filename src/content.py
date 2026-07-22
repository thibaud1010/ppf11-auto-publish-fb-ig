"""Lectura del pool de contenido (CSV) y renderizado de captions."""
import csv
import json
from collections import defaultdict

from .config import CONTENT_DIR, CONFIG_DIR

# columnas esperadas en los CSV: language,title,summary,url,image_url,hashtags
# OJO: en el CSV 'hashtags' guarda SOLO el tag de tema; los hashtags base por
# idioma viven en config/hashtags.json y se anteponen aqui al cargar.

_BASE_HASHTAGS = None


def _base_hashtags():
    """Cachea los hashtags base por idioma desde config/hashtags.json."""
    global _BASE_HASHTAGS
    if _BASE_HASHTAGS is None:
        path = CONFIG_DIR / "hashtags.json"
        _BASE_HASHTAGS = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            _BASE_HASHTAGS = {
                k.lower(): v for k, v in data.items() if not k.startswith("_")
            }
    return _BASE_HASHTAGS


def load_items(kind, language):
    """kind = 'articles' | 'exercises'. Devuelve las filas del idioma dado."""
    path = CONTENT_DIR / f"{kind}.csv"
    base = _base_hashtags().get(language.lower(), "")
    items = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("language") or "").strip().lower() == language.lower():
                # normaliza espacios
                clean = {k: (v or "").strip() for k, v in row.items()}
                if clean.get("url") and clean.get("image_url"):
                    # antepone los hashtags base al tag de tema del CSV
                    merged = f"{base} {clean.get('hashtags', '')}".strip()
                    clean["hashtags"] = " ".join(merged.split())
                    items.append(clean)
    return items


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render_caption(template, row):
    """Rellena la plantilla con las columnas de la fila. Claves ausentes se dejan tal cual."""
    return template.format_map(_SafeDict(row))
