"""Publicacion en Paginas de Facebook via Graph API.

Publica una FOTO con el enlace dentro del texto (asi la imagen propia se ve
grande y el enlace queda clicable en el caption).
"""
import requests

from .config import FB_HOST


def publish_photo(page_id, page_token, image_url, caption, timeout=60):
    resp = requests.post(
        f"{FB_HOST}/{page_id}/photos",
        data={"url": image_url, "caption": caption, "access_token": page_token},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"FB {resp.status_code}: {resp.text}")
    return resp.json()


def publish_comment(post_id, page_token, message, timeout=60):
    """Comenta el post (para poner ahi los enlaces: FB entierra fotos con enlace en el caption).

    Reintenta: justo despues de subir un VIDEO, FB aun lo esta procesando y rechaza
    el comentario (visto en de y en la prueba de pl del 2026-11-25; un minuto despues
    el mismo comentario entra sin problema)."""
    import time
    for intento in range(6):
        resp = requests.post(
            f"{FB_HOST}/{post_id}/comments",
            data={"message": message, "access_token": page_token},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
        if intento < 5:
            time.sleep(20)
    raise RuntimeError(f"FB comment {resp.status_code}: {resp.text}")
