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


def _container_status(host, creation_id, token, timeout=30):
    """Devuelve el status_code del contenedor: IN_PROGRESS / FINISHED / ERROR / EXPIRED."""
    resp = requests.get(
        f"{host}/{creation_id}",
        params={"fields": "status_code", "access_token": token},
        timeout=timeout,
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("status_code")


def publish(ig_user_id, token, image_url, caption, host=FB_HOST, poll_retries=12, wait=5):
    """Publica una imagen SIN riesgo de duplicar.

    Flujo correcto de la Content Publishing API:
      1) crear el contenedor
      2) ESPERAR a que el contenedor este FINISHED (sondeando su estado)
      3) publicar UNA SOLA VEZ

    BUG ANTERIOR (causaba duplicados): se reintentaba el `media_publish` hasta 8
    veces esperando un 200. Si Instagram YA habia publicado pero la respuesta no
    llegaba como 200 (timeout / error transitorio), el reintento creaba un SEGUNDO
    post = DUPLICADO. Aqui el publish se llama UNA sola vez y NO se reintenta.
    """
    creation_id = _create_container(host, ig_user_id, token, image_url, caption)
    # esperar a que el contenedor este listo antes de publicar
    status = None
    for _ in range(poll_retries):
        status = _container_status(host, creation_id, token)
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"IG contenedor {status} (creation_id={creation_id})")
        time.sleep(wait)
    if status != "FINISHED":
        raise RuntimeError(f"IG contenedor no llego a FINISHED (ultimo estado={status})")
    # PUBLICAR UNA SOLA VEZ: si falla, NO reintentar (reintentar podria duplicar).
    resp = _publish_container(host, ig_user_id, token, creation_id)
    if resp.status_code != 200:
        raise RuntimeError(f"IG publish {resp.status_code}: {resp.text}")
    return resp.json()
