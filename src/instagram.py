"""Publicacion en cuentas de Instagram (Content Publishing API).

SISTEMA MIXTO (segun accounts.json -> instagram.mode). El motor pasa el `host`
y el `token` correctos por cuenta; este modulo solo ejecuta la publicacion:
  - mode "page"  (es/fr/nl): host = graph.facebook.com, token = FB_TOKEN de la Pagina.
  - mode "login" (en/it/de/pt): host = graph.instagram.com, token = IG_TOKEN de la cuenta.

En ambos casos el flujo es el mismo (Content Publishing API), en 2 pasos:
  1) crear el contenedor de media (image_url debe ser una URL PUBLICA jpg/png)
  2) publicar el contenedor

IMPORTANTE: Instagram NO admite subir un archivo local; la imagen debe estar
accesible en una URL publica (normalmente la og:image de tu web ya vale).
"""
import time

import requests

from .config import FB_HOST


def _create_container(host, ig_user_id, token, image_url, caption, timeout=60):
    resp = requests.post(
        f"{host}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"IG create {resp.status_code}: {resp.text}")
    return resp.json()["id"]


def _publish_container(host, ig_user_id, token, creation_id, timeout=60):
    resp = requests.post(
        f"{host}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=timeout,
    )
    return resp


def publish(ig_user_id, token, image_url, caption, host=FB_HOST, retries=8, wait=5):
    """Publica una imagen. `host` = FB_HOST (mode page) o IG_LOGIN_HOST (mode login)."""
    creation_id = _create_container(host, ig_user_id, token, image_url, caption)
    # el contenedor puede tardar unos segundos en estar listo
    last = None
    for _ in range(retries):
        resp = _publish_container(host, ig_user_id, token, creation_id)
        if resp.status_code == 200:
            return resp.json()
        last = resp
        time.sleep(wait)
    raise RuntimeError(
        f"IG publish fallo tras {retries} intentos: "
        f"{last.status_code if last else '?'}: {last.text if last else ''}"
    )
