"""Horario de publicacion: hora AL AZAR dentro de una franja, por dia e idioma.

Antes cada cuenta publicaba al mismo minuto todos los dias (07:02, 12:02, 18:02).
Ahora config/schedule.json define, por idioma, la hora LOCAL de inicio de cada
franja (morning / midday / evening) y su zona horaria; la hora real de cada dia
cae al azar dentro de [inicio, inicio + window_minutes]. El azar es DETERMINISTA
(hash de dia+idioma+post): todos los disparos del dia calculan la misma hora.

El sistema se dispara cada pocos minutos (.github/workflows/tick.yml) y cada
publicador pregunta aqui que idiomas "tocan" ahora. La marca de hecho va por
dia LOCAL + post + idioma en state/published.json, asi que disparar muchas veces
nunca duplica.
"""
import datetime
import hashlib

from .config import CONFIG_DIR, load_json
from . import state as st

# post -> franja de config/schedule.json
POSTS = {
    "fb:article": "morning",
    "ig:morning": "morning",
    "reels": "midday",
    "fb:exercise": "evening",
    "ig:evening": "evening",
}

# respaldo si no hay base de datos de zonas (Windows sin el paquete tzdata)
_FIXED_OFFSETS = {"America/Bogota": -5, "Europe/Paris": 2}


def _config():
    return load_json(CONFIG_DIR / "schedule.json")


def _lang_cfg(cfg, lang):
    return {**cfg["default"], **cfg.get(lang, {})}


def local_now(tz, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return now.astimezone(ZoneInfo(tz))
    except Exception:  # noqa: BLE001
        off = datetime.timezone(datetime.timedelta(hours=_FIXED_OFFSETS.get(tz, 0)))
        return now.astimezone(off)


def planned(lang, post, now=None):
    """(clave_del_dia, hora_planificada, fin_del_margen) en hora local del idioma."""
    cfg = _config()
    lc = _lang_cfg(cfg, lang)
    local = local_now(lc["tz"], now)
    day = local.strftime("%Y-%m-%d")
    hh, mm = (int(x) for x in lc[POSTS[post]].split(":"))
    start = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    seed = hashlib.sha256(f"{day}:{lang}:{post}".encode()).digest()
    offset = int.from_bytes(seed[:4], "big") % (int(cfg["window_minutes"]) + 1)
    when = start + datetime.timedelta(minutes=offset)
    end = start + datetime.timedelta(minutes=int(cfg["window_minutes"]) + int(cfg["grace_minutes"]))
    return f"{day}:{post}:{lang}", when, end


def due(lang, post, now=None):
    """Clave de hecho si a `lang` le toca publicar `post` AHORA y aun no lo hizo; si no, None."""
    key, when, end = planned(lang, post, now)
    local = local_now(_lang_cfg(_config(), lang)["tz"], now)
    if when <= local < end and not st.is_done(key):
        return key
    return None


def nearest(lang, posts, now=None):
    """Clave de hecho del post de `posts` cuya hora planificada cae mas cerca de ahora
    (para --force: publicar ya, contando como la franja que corresponde)."""
    local = local_now(_lang_cfg(_config(), lang)["tz"], now)
    plans = [planned(lang, p, now) for p in posts]
    return min(plans, key=lambda x: abs((x[1] - local).total_seconds()))[0]
