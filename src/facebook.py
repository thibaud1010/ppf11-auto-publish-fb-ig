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
