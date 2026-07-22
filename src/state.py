"""Registro de lo ya publicado para rotar el contenido y no repetir.

Se identifica cada item por su IMAGE_URL (campo unico por item). OJO: no se usa
`url`, porque en ppf11 los 100 ejercicios de un idioma comparten UNA sola URL
(pagina-biblioteca sin detalle); rotar por `url` publicaria siempre el mismo.

Estructura de state/posted_log.json:
{
  "ig:es:exercises": ["image_url1", "image_url2", ...],  # orden de publicacion (mas reciente al final)
  "fb:es:articles":  ["image_urlA", ...],
  ...
}
"""
import json

from .config import STATE_DIR

# campo que identifica de forma unica cada item (ver nota arriba)
IDENTITY = "image_url"


def _path():
    STATE_DIR.mkdir(exist_ok=True)
    return STATE_DIR / "posted_log.json"


def load_state():
    p = _path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    _path().write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def pick_next(items, key, state):
    """Elige el item menos-recientemente publicado (o el primero no publicado)."""
    if not items:
        return None
    posted = state.get(key, [])
    # 1) primer item que aun no se ha publicado nunca
    for it in items:
        if it[IDENTITY] not in posted:
            return it
    # 2) todos publicados -> el mas antiguo (frente de la lista) que siga existiendo
    for ident in posted:
        for it in items:
            if it[IDENTITY] == ident:
                return it
    return items[0]


def mark_posted(state, key, ident, cap=500):
    lst = [u for u in state.get(key, []) if u != ident]
    lst.append(ident)
    state[key] = lst[-cap:]
