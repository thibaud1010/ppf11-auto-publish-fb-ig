"""Ejercicios ANIMADOS (video) por idioma — sustituyen a los ejercicios en imagen.

Catalogo: content/exercise_videos.json -> {"de": [{id, title, drive_id, caption_fb, caption_ig}, ...]}
  - Rotacion en el orden del catalogo (01 -> 30) y vuelta a empezar: con 1 al dia,
    30 videos = 2 vueltas en ~2 meses (ver src/state.pick_next).
  - Un idioma sin lista no publica ejercicio (ni FB tarde ni IG manana).

Alojamiento: Meta necesita una URL PUBLICA del mp4. El video se descarga del Drive
(compartido por enlace) y se cachea en Supabase (bucket publico, carpeta
ejercicios/<lang>/) la primera vez; despues se reutiliza esa URL.
"""
import json
import os
import tempfile

import requests

from .config import CONTENT_DIR
from . import reels_publish as rp

CATALOG = CONTENT_DIR / "exercise_videos.json"
DRIVE_DL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"


def load(lang):
    """Items del idioma, con 'image_url' = identidad de rotacion (compat. con state.py)."""
    if not CATALOG.exists():
        return []
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = []
    for it in data.get(lang, []):
        it = dict(it)
        it["image_url"] = f"video:{lang}:{it['id']}"   # identidad estable en posted_log
        it["url"] = it.get("url", "")
        items.append(it)
    return items


def public_url(item, lang):
    """URL publica del mp4 en Supabase; lo sube desde el Drive si aun no esta."""
    sb_url = os.environ["SUPABASE_URL"].rstrip("/")
    sb_key = os.environ["SUPABASE_KEY"]
    bucket = os.environ.get("SUPABASE_BUCKET") or "videos"
    if item.get("path"):   # ya subido a mano (p.ej. es/, con musica anadida)
        return f"{sb_url}/storage/v1/object/public/{bucket}/{item['path']}"
    filename = f"ejercicios/{lang}/{item['id']}.mp4"
    url = f"{sb_url}/storage/v1/object/public/{bucket}/{filename}"
    h = requests.head(url, timeout=30)
    if h.status_code == 200 and int(h.headers.get("content-length", "0") or 0) > 10000:
        return url
    print(f"[VIDEO][{lang}] {item['id']} no esta en Supabase; descargando del Drive…")
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "v.mp4")
        with requests.get(DRIVE_DL.format(item["drive_id"]), stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        with open(dest, "rb") as f:
            if f.read(12)[4:8] != b"ftyp":
                raise RuntimeError(f"Drive {item['drive_id']}: no devolvio un mp4 (¿compartido por enlace?)")
        return rp.supabase_upload(dest, bucket, filename, sb_url, sb_key)
