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

from src.config import FB_HOST, IG_LOGIN_HOST, get_token, load_accounts
from src import state as st
from src import reels_publish as rp

CONFIG = os.path.join(os.path.dirname(__file__), "config", "reels.json")
STATE_KEY = "reels:posted"  # lista de reel_id ya publicados (rotación sin repetir)


def load_reels():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)["reels"]


def pick_next_reel(reels, posted):
    uniques = [r for r in reels if not r.get("duplicate_of")]
    for r in uniques:
        if r["reel_id"] not in posted:
            return r
    # todos publicados -> reiniciar ciclo
    return uniques[0] if uniques else None


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

    print(f"[REELS] siguiente: #{reel['n']} {reel['fb_url']} (tema {reel['theme_fr']})")
    print(f"[REELS] idiomas: {', '.join(langs)}  | modo: {'DRY-RUN' if dry else 'PUBLICAR'}")

    if dry:
        for l in langs:
            print(f"\n----- {l} -----\n{reel['captions'][l]}")
        print("\n[REELS] DRY-RUN: no se publica nada. Usa --publish (con secretos) para lanzar.")
        return

    # ---- publicación real (WIP: validar) ----
    sb_url = os.environ["SUPABASE_URL"].rstrip("/")
    sb_key = os.environ["SUPABASE_KEY"]
    sb_bucket = os.environ.get("SUPABASE_BUCKET", "reels")

    tmp = os.path.join(tempfile.gettempdir(), f"reel_{reel['reel_id']}.mp4")
    fr_token = get_token("FB_TOKEN_FR")  # la Página FR posee los reels
    print("[REELS] descargando vídeo del reel FR…")
    rp.download_fb_reel(reel["reel_id"], fr_token, tmp)
    filename = f"reel_{reel['reel_id']}.mp4"
    print("[REELS] subiendo a Supabase…")
    public_url = rp.supabase_upload(tmp, sb_bucket, filename, sb_url, sb_key)
    print(f"[REELS] URL pública: {public_url}")

    ok, fail = 0, 0
    for l in langs:
        cfg = accounts[l]
        caption = reel["captions"][l]
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
        # Facebook vídeo
        try:
            res = rp.fb_publish_video(cfg["facebook"]["page_id"], get_token(f"FB_TOKEN_{l.upper()}"),
                                      public_url, caption)
            print(f"[REELS][FB][{l}] OK {res.get('id')}")
            st.log_history({"platform": "fb", "lang": l, "type": "reel",
                            "reel_id": reel["reel_id"], "status": "ok", "post_id": res.get("id", "")})
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[REELS][FB][{l}] ERROR: {e}")
            st.log_history({"platform": "fb", "lang": l, "type": "reel",
                            "reel_id": reel["reel_id"], "status": "error", "error": str(e)[:200]})
            fail += 1

    if ok:
        posted.append(reel["reel_id"])
        state[STATE_KEY] = posted[-200:]
        st.save_state(state)
    try:
        rp.supabase_delete(sb_bucket, filename, sb_url, sb_key)  # limpieza (no se acumula)
    except Exception:  # noqa: BLE001
        pass
    print(f"[REELS] terminado ok={ok} fail={fail}")
    sys.exit(1 if fail and not ok else 0)


if __name__ == "__main__":
    main()
