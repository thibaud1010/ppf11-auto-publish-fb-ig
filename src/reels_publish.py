"""Funciones de publicación de REELS/vídeo — BORRADOR (WIP).

⚠️ PENDIENTE DE VALIDAR con datos reales (bucket Supabase + 1 prueba). Ver publish_reels.py.

Flujo por reel:
  1) descargar el vídeo del reel FR de PPF11 (Graph API, la Página FR posee el reel)
  2) subirlo a un bucket PÚBLICO de Supabase Storage -> URL pública
  3) publicar como Reel en cada cuenta IG (6 idiomas) + como vídeo en cada Página FB
     con el caption del idioma (config/reels.json).

Notas de API (a confirmar en la prueba):
  - IG Reels: contenedor media_type=REELS + video_url, esperar status FINISHED, luego media_publish.
  - FB: /{page_id}/videos con file_url = vídeo en el feed. Para Reel FB "puro" haría falta
    el flujo /video_reels en 3 fases (start/transfer/finish) — se puede cambiar tras validar.
"""
import time
import urllib.request

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def download_fb_reel(reel_id, fb_token, dest):
    """Descarga el MP4 del reel (la Página FR debe poseerlo). Devuelve `dest`."""
    r = requests.get(f"{GRAPH}/{reel_id}",
                     params={"fields": "source", "access_token": fb_token}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"FB reel {reel_id} GET {r.status_code}: {r.text[:200]}")
    src = r.json().get("source")
    if not src:
        raise RuntimeError(f"FB reel {reel_id}: respuesta sin 'source' -> {r.text[:200]}")
    urllib.request.urlretrieve(src, dest)
    return dest


def supabase_upload(local_path, bucket, filename, sb_url, sb_key):
    """Sube el vídeo a Supabase Storage (upsert) y devuelve la URL PÚBLICA."""
    with open(local_path, "rb") as f:
        data = f.read()
    url = f"{sb_url}/storage/v1/object/{bucket}/{filename}"
    r = requests.post(url, data=data, timeout=300, headers={
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "video/mp4",
        "x-upsert": "true",
    })
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Supabase upload {r.status_code}: {r.text[:200]}")
    return f"{sb_url}/storage/v1/object/public/{bucket}/{filename}"


def supabase_delete(bucket, filename, sb_url, sb_key):
    requests.delete(f"{sb_url}/storage/v1/object/{bucket}/{filename}",
                    headers={"Authorization": f"Bearer {sb_key}"}, timeout=60)


def ig_publish_reel(host, ig_user_id, token, video_url, caption, retries=40, wait=6):
    """IG Reel: crea contenedor REELS, espera procesado, publica. Devuelve la respuesta."""
    r = requests.post(f"{host}/{ig_user_id}/media", timeout=60, data={
        "media_type": "REELS", "video_url": video_url,
        "caption": caption, "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(f"IG reel create {r.status_code}: {r.text}")
    cid = r.json()["id"]
    for _ in range(retries):
        s = requests.get(f"{host}/{cid}", timeout=30,
                         params={"fields": "status_code", "access_token": token})
        code = (s.json() or {}).get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"IG reel procesado ERROR: {s.text}")
        time.sleep(wait)
    else:
        raise RuntimeError("IG reel: timeout esperando el procesado del vídeo")
    p = requests.post(f"{host}/{ig_user_id}/media_publish", timeout=60,
                      data={"creation_id": cid, "access_token": token})
    if p.status_code != 200:
        raise RuntimeError(f"IG reel publish {p.status_code}: {p.text}")
    return p.json()


def fb_publish_video(page_id, token, video_url, caption):
    """Publica un vídeo en la Página FB (feed). VALIDAR si se prefiere Reel FB puro (/video_reels)."""
    r = requests.post(f"{GRAPH}/{page_id}/videos", timeout=300, data={
        "file_url": video_url, "description": caption, "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(f"FB video {page_id} {r.status_code}: {r.text}")
    return r.json()


def fb_publish_reel(page_id, token, video_url, caption, retries=40, wait=6):
    """Publica un REEL FB PURO en la Página vía /video_reels (3 fases).

    Se usa cuando el crosspost nativo IG→FB NO está disponible (cuentas en/de/it/pt,
    cuya Página no se puede enlazar a su IG por la sanción de ads del negocio). Un Reel
    FB puro entra en el feed de reels (no como vídeo de feed enterrado que da ~0 alcance).

    Fases: start (obtiene video_id + upload_url) → subida ALOJADA (FB descarga el mp4
    de la URL pública de Supabase) → finish con video_state=PUBLISHED. Devuelve {id}.
    """
    # 1) start
    r = requests.post(f"{GRAPH}/{page_id}/video_reels", timeout=60,
                      data={"upload_phase": "start", "access_token": token})
    if r.status_code != 200:
        raise RuntimeError(f"FB reel start {page_id} {r.status_code}: {r.text[:200]}")
    j = r.json()
    video_id, upload_url = j["video_id"], j["upload_url"]
    # 2) subida alojada: FB descarga el vídeo de la URL pública (header file_url)
    u = requests.post(upload_url, timeout=300,
                      headers={"Authorization": f"OAuth {token}", "file_url": video_url})
    if u.status_code != 200:
        raise RuntimeError(f"FB reel upload {video_id} {u.status_code}: {u.text[:200]}")
    # 3) esperar a que el vídeo esté subido/procesado antes de publicar
    for _ in range(retries):
        s = requests.get(f"{GRAPH}/{video_id}", timeout=30,
                         params={"fields": "status", "access_token": token}).json()
        vs = ((s.get("status") or {}).get("video_status") or "").lower()
        if vs in ("ready", "upload_complete", "processing_complete", "complete"):
            break
        if vs == "error":
            raise RuntimeError(f"FB reel {video_id} status error: {s}")
        time.sleep(wait)
    # 4) finish + publicar
    f = requests.post(f"{GRAPH}/{page_id}/video_reels", timeout=60, data={
        "upload_phase": "finish", "video_id": video_id,
        "video_state": "PUBLISHED", "description": caption, "access_token": token})
    if f.status_code != 200:
        raise RuntimeError(f"FB reel finish {video_id} {f.status_code}: {f.text[:200]}")
    return {"id": video_id}
