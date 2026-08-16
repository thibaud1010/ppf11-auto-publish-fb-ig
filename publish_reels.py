#!/usr/bin/env python3
"""Publica UN reel de PPF11 (rotación) en IG + FB de los 6 idiomas — BORRADOR (WIP).

⚠️ NO ACTIVO todavía: solo workflow_dispatch manual y DRY-RUN por defecto.
Pendiente para activarlo de verdad:
  - Bucket PÚBLICO en Supabase + secretos SUPABASE_URL / SUPABASE_KEY (service_role) / SUPABASE_BUCKET.
  - Validar 1 reel real (descarga FB + publicación IG Reel) — usar --publish --only es.
  - Decidir hora (mediodía) y crear el disparo en cron-job.org (como los otros).

Uso:
  python publish_reels.py                 # DRY-RUN: muestra qué reel y captions saldrían
  python publish_reels.py --publish       # publica de verdad (necesita secretos)
  python publish_reels.py --publish --only es
"""
import argparse
import json
import os
import sys
import tempfile

import requests

from src.config import FB_HOST, IG_LOGIN_HOST, get_token, load_accounts
from src import state as st
from src import reels_publish as rp

CONFIG = os.path.join(os.path.dirname(__file__), "config", "reels.json")
STATE_KEY = "reels:posted"    # lista de reel_id por RECENCIA (rotación sin repetir)
STATE_COUNT = "reels:count"   # {reel_id: veces publicado} -> alterna caption A/B


def pick_caption(reel, lang, veces):
    """Caption del reel: alterna version A y B para que el repost NO sea identico.

    veces par (0, 2, 4...) -> A (regalo: 50 ejercicios en PDF)
    veces impar (1, 3...)  -> B (regalo: guia de los jovenes futbolistas)
    """
    if veces % 2 == 1:
        return (reel.get("captions_b") or reel["captions"])[lang]
    return reel["captions"][lang]


def load_reels():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)["reels"]


def pick_next_reel(reels, posted):
    """Siguiente reel a publicar. Rotacion INFINITA sin repetir.

    Ciclo 1: los reels nunca publicados, en el orden de config/reels.json.
    Ciclos siguientes: el MENOS RECIENTE (posted esta ordenado por recencia,
    el mas antiguo primero), evitando que salgan dos reels del MISMO TEMA en
    dias seguidos -> el ciclo 2 no repite el orden del ciclo 1 y la variedad
    dia a dia se mantiene.

    BUG ANTERIOR: al acabarse los 30 devolvia siempre uniques[0], asi que a
    partir del dia 31 habria publicado el MISMO reel todos los dias.
    """
    uniques = [r for r in reels if not r.get("duplicate_of")]
    if not uniques:
        return None

    nunca = [r for r in uniques if r["reel_id"] not in posted]
    if nunca:
        return nunca[0]

    # ciclo nuevo: del mas antiguo al mas reciente
    orden = sorted(uniques, key=lambda r: posted.index(r["reel_id"]))
    ultimo = posted[-1] if posted else None
    tema_ultimo = next((r.get("theme_fr") for r in uniques if r["reel_id"] == ultimo), None)
    for r in orden:
        if r.get("theme_fr") != tema_ultimo:
            return r
    return orden[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="publicar de verdad (por defecto dry-run)")
    ap.add_argument("--only", help="solo este idioma")
    args = ap.parse_args()
    dry = not args.publish

    reels = load_reels()
    state = st.load_state()
    posted = state.get(STATE_KEY, [])
    reel = pick_next_reel(reels, posted)
    if not reel:
        print("[REELS] no hay reels en config/reels.json"); return

    accounts = load_accounts()["languages"]
    langs = [l for l in ["es", "en", "de", "it", "pt", "nl"]
             if accounts.get(l, {}).get("enabled", True) and (not args.only or l == args.only)]

    veces = state.get(STATE_COUNT, {}).get(reel["reel_id"], 0)
    version = "B (guia jovenes)" if veces % 2 else "A (50 ejercicios)"

    print(f"[REELS] siguiente: #{reel['n']} {reel['fb_url']} (tema {reel['theme_fr']})")
    print(f"[REELS] publicado {veces} vez/veces antes -> caption version {version}")
    print(f"[REELS] idiomas: {', '.join(langs)}  | modo: {'DRY-RUN' if dry else 'PUBLICAR'}")

    if dry:
        for l in langs:
            print(f"\n----- {l} -----\n{pick_caption(reel, l, veces)}")
        print("\n[REELS] DRY-RUN: no se publica nada. Usa --publish (con secretos) para lanzar.")
        return

    # ---- publicación real (WIP: validar) ----
    sb_url = os.environ["SUPABASE_URL"].rstrip("/")
    sb_key = os.environ["SUPABASE_KEY"]
    with open(CONFIG, encoding="utf-8") as f:
        sup = json.load(f).get("supabase", {})
    bucket = os.environ.get("SUPABASE_BUCKET") or sup.get("bucket", "videos")
    folder = os.environ.get("SUPABASE_FOLDER") or sup.get("folder", "")
    filename = (folder + "/" if folder else "") + f"reel_{reel['reel_id']}.mp4"
    public_url = f"{sb_url}/storage/v1/object/public/{bucket}/{filename}"

    # el vídeo debería estar YA en el bucket (sembrado con tools/seed_reels_bucket.py);
    # si no está, se descarga de FB y se sube en el momento.
    if requests.get(public_url, stream=True, timeout=30).status_code != 200:
        tmp = os.path.join(tempfile.gettempdir(), f"reel_{reel['reel_id']}.mp4")
        print("[REELS] no está en el bucket; descargando de FB y subiendo…")
        rp.download_fb_reel(reel["reel_id"], get_token("FB_TOKEN_FR"), tmp)
        public_url = rp.supabase_upload(tmp, bucket, filename, sb_url, sb_key)
    print(f"[REELS] URL pública: {public_url}")

    ok, fail = 0, 0
    for l in langs:
        cfg = accounts[l]
        caption = pick_caption(reel, l, veces)
        # Instagram Reel
        try:
            ig = cfg["instagram"]
            if ig.get("mode") == "login":
                host, token = IG_LOGIN_HOST, get_token(f"IG_TOKEN_{l.upper()}")
            else:
                host, token = FB_HOST, get_token(f"FB_TOKEN_{l.upper()}")
            res = rp.ig_publish_reel(host, ig["ig_user_id"], token, public_url, caption)
            print(f"[REELS][IG][{l}] OK {res.get('id')}")
            st.log_history({"platform": "ig", "lang": l, "type": "reel",
                            "reel_id": reel["reel_id"], "status": "ok", "post_id": res.get("id", "")})
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[REELS][IG][{l}] ERROR: {e}")
            st.log_history({"platform": "ig", "lang": l, "type": "reel",
                            "reel_id": reel["reel_id"], "status": "error", "error": str(e)[:200]})
            fail += 1
        # Facebook: YA NO se sube el video por API. Auditoria 03-08-2026: la subida
        # directa via /videos quedaba enterrada por FB (2 vistas), mientras que los
        # reels CROSSPOSTEADOS de IG->FB alcanzaban 3K-130K. El reel llega a la
        # Pagina FB via el crosspost automatico configurado en cada cuenta de IG
        # ("Compartir en Facebook"), no desde aqui.
        print(f"[REELS][FB][{l}] omitido (llega via crosspost automatico IG→FB)")

    if ok:
        # quitar-y-anadir: 'posted' queda ordenado por RECENCIA (el mas antiguo
        # primero), que es lo que usa pick_next_reel para rotar sin repetir.
        posted = [x for x in posted if x != reel["reel_id"]]
        posted.append(reel["reel_id"])
        state[STATE_KEY] = posted[-200:]
        # veces publicado -> la proxima vez sale la OTRA version del caption
        cuenta = state.get(STATE_COUNT, {})
        cuenta[reel["reel_id"]] = veces + 1
        state[STATE_COUNT] = cuenta
        st.save_state(state)
    # el vídeo se queda en el bucket (sembrado, se reutiliza en la rotación).
    print(f"[REELS] terminado ok={ok} fail={fail}")
    sys.exit(1 if fail and not ok else 0)


if __name__ == "__main__":
    main()
