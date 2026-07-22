"""Carga de configuracion, plantillas y tokens.

- Los IDs (page_id, ig_user_id) NO son secretos -> viven en config/accounts.json
- Los tokens SI son secretos -> se leen de:
    1) la variable de entorno TOKENS_JSON (un JSON {"FB_TOKEN_ES": "...", ...})
    2) el fichero config/secrets.json (gitignored)
    3) variables de entorno sueltas (FB_TOKEN_ES, IG_TOKEN_ES, ...)
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
CONTENT_DIR = ROOT / "content"
STATE_DIR = ROOT / "state"

GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v21.0")
# Host para Facebook (Graph API clasica)
FB_HOST = f"https://graph.facebook.com/{GRAPH_VERSION}"
# SISTEMA MIXTO por cuenta (segun accounts.json -> instagram.mode):
#  - mode "page"  (es/fr/nl): IG vinculado a la Pagina -> se publica con el TOKEN DE
#    LA PAGINA via graph.facebook.com (FB_HOST). Token = FB_TOKEN_<LANG> (permanente).
#  - mode "login" (en/it/de/pt): Instagram Login -> se publica via graph.instagram.com
#    (IG_LOGIN_HOST) con el token PROPIO de la cuenta IG. Token = IG_TOKEN_<LANG> (60 dias).
IG_LOGIN_HOST = f"https://graph.instagram.com/{GRAPH_VERSION}"
# Compat: IG_HOST antiguo (por si algun codigo lo referencia); apunta a Facebook.
IG_HOST = os.environ.get("IG_HOST", FB_HOST)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_accounts():
    return load_json(CONFIG_DIR / "accounts.json")


def load_templates():
    return load_json(CONFIG_DIR / "templates.json")


# ---- tokens -------------------------------------------------------------
_TOKENS = {}


def _load_tokens():
    raw = os.environ.get("TOKENS_JSON")
    if raw:
        try:
            _TOKENS.update(json.loads(raw))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"TOKENS_JSON no es JSON valido: {e}")
    secrets_path = CONFIG_DIR / "secrets.json"
    if secrets_path.exists():
        _TOKENS.update(load_json(secrets_path))


_load_tokens()


def get_token(name):
    """Devuelve el token por nombre (p.ej. FB_TOKEN_ES o IG_TOKEN_ES)."""
    if name in _TOKENS:
        return _TOKENS[name]
    value = os.environ.get(name)
    if value:
        return value
    raise RuntimeError(
        f"Falta el token '{name}'. Anadelo en config/secrets.json, "
        f"en TOKENS_JSON o como variable de entorno."
    )
