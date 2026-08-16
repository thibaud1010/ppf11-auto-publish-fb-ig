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
import datetime
import json
import math

from .config import STATE_DIR

# campo que identifica de forma unica cada item (ver nota arriba)
IDENTITY = "image_url"


def log_history(record):
    """Anade una linea al historico de publicaciones (state/history.jsonl)."""
    STATE_DIR.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = json.dumps({"ts": now, **record}, ensure_ascii=False)
    with open(STATE_DIR / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---- idempotencia: publicar una sola vez por franja y dia (hora de Paris) ----
def paris_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:  # noqa: BLE001 (fallback: UTC+2 aprox)
        return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)


def _published_path():
    STATE_DIR.mkdir(exist_ok=True)
    return STATE_DIR / "published.json"


def _published_load():
    p = _published_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def already_published(slot):
    """slot p.ej. 'fb:article' o 'ig:morning'. True si ya se publico HOY (Paris)."""
    key = f"{paris_now().strftime('%Y-%m-%d')}:{slot}"
    return _published_load().get(key) is True


def mark_published(slot):
    data = _published_load()
    data[f"{paris_now().strftime('%Y-%m-%d')}:{slot}"] = True
    # conserva solo las ultimas ~40 marcas
    if len(data) > 40:
        for k in sorted(data)[:-40]:
            del data[k]
    _published_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


# ---- desincronizacion por idioma (auditoria 16-08-2026) -----------------
# Las 6 Paginas ppf11 publicaban LA MISMA imagen el MISMO dia: comparten
# image_url y todas recorrian el catalogo en el mismo orden desde el mismo
# sitio (verificado: 1 sola image_url distinta en 6 Paginas, todos los dias).
# Para Facebook eso es contenido duplicado en 6 sitios a la vez -> principal
# sospechoso del alcance 0 (el fix del 03-08 desfaso la HORA, no la IMAGEN).
# Cada idioma recorre el MISMO catalogo con su propio punto de partida Y su
# propio paso. Solo desplazar el inicio NO bastaba: como todos habian publicado
# el mismo tramo inicial, el "primer item nunca publicado" volvia a coincidir
# (probado: es y en seguian eligiendo la misma imagen). Con un paso distinto
# por idioma las secuencias divergen de verdad y siguen cubriendo el catalogo
# entero exactamente una vez (paso coprimo con el numero de items).
LANG_ORDER = ["es", "en", "fr", "de", "it", "pt", "nl"]
_STRIDES = [7, 11, 13, 17, 19, 23, 29]


def order_for_language(items, lang):
    """Devuelve `items` en el orden propio del idioma (misma lista, otro recorrido)."""
    n = len(items)
    if n < 2:
        return items
    try:
        pos = LANG_ORDER.index((lang or "").lower())
    except ValueError:
        pos = 0
    offset = (pos * n) // len(LANG_ORDER)
    rotated = _STRIDES[pos:] + _STRIDES[:pos]
    stride = next((s for s in rotated if math.gcd(s, n) == 1), 1)
    return [items[(offset + i * stride) % n] for i in range(n)]


def pick_next(items, key, state, exclude=None):
    """Elige el item menos-recientemente publicado (o el primero no publicado).

    `exclude` = identidades ya usadas por OTRO idioma en esta misma ejecucion.
    Garantiza que dos Paginas nunca publiquen la MISMA imagen el mismo dia,
    aunque sus historiales coincidan (el orden por idioma solo lo hace muy
    improbable; esto lo hace imposible).
    """
    if not items:
        return None
    exclude = exclude or set()
    posted = state.get(key, [])
    # 1) primer item que aun no se ha publicado nunca
    for it in items:
        if it[IDENTITY] not in posted and it[IDENTITY] not in exclude:
            return it
    # 2) todos publicados -> el mas antiguo (frente de la lista) que siga existiendo
    for ident in posted:
        for it in items:
            if it[IDENTITY] == ident and it[IDENTITY] not in exclude:
                return it
    # 3) todo excluido (catalogo mas corto que el numero de idiomas): sin filtro
    for it in items:
        if it[IDENTITY] not in posted:
            return it
    return items[0]


def mark_posted(state, key, ident, cap=500):
    lst = [u for u in state.get(key, []) if u != ident]
    lst.append(ident)
    state[key] = lst[-cap:]
