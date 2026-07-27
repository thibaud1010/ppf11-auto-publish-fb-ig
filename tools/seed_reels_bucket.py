#!/usr/bin/env python3
"""Siembra el bucket: descarga TODOS los reels FR (una vez) y los sube a Supabase.

Deja en el bucket `reel_<id>.mp4` por cada reel único de config/reels.json.
Luego el diario (publish_reels.py) solo elige uno y publica — sin volver a descargar.

Requiere (env / secretos):
  TOKENS_JSON (con FB_TOKEN_FR)  ·  SUPABASE_URL  ·  SUPABASE_KEY (service_role)  ·  SUPABASE_BUCKET

Uso:  python tools/seed_reels_bucket.py            # todos los que falten
      python tools/seed_reels_bucket.py --force    # re-subir aunque ya existan
      python tools/seed_reels_bucket.py --only 1   # solo el reel nº 1 (para probar)
"""
import argparse
import json
import os
import sys
import tempfile

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.config import get_token          # noqa: E402
from src import reels_publish as rp        # noqa: E402

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "reels.json")


def exists_in_bucket(sb_url, bucket, filename):
    r = requests.get(f"{sb_url}/storage/v1/object/public/{bucket}/{filename}",
                     stream=True, timeout=30)
    return r.status_code == 200


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", type=int, help="solo el reel con este nº")
    args = ap.parse_args()

    with open(CONFIG, encoding="utf-8") as f:
        reels = json.load(f)["reels"]
    reels = [r for r in reels if not r.get("duplicate_of")]
    if args.only:
        reels = [r for r in reels if r["n"] == args.only]

    sb_url = os.environ["SUPABASE_URL"].rstrip("/")
    sb_key = os.environ["SUPABASE_KEY"]
    bucket = os.environ.get("SUPABASE_BUCKET", "reels")
    fr_token = get_token("FB_TOKEN_FR")

    done, skip, fail = 0, 0, 0
    for r in reels:
        fn = f"reel_{r['reel_id']}.mp4"
        if not args.force and exists_in_bucket(sb_url, bucket, fn):
            print(f"[seed] #{r['n']} ya está -> se omite")
            skip += 1
            continue
        tmp = os.path.join(tempfile.gettempdir(), fn)
        try:
            rp.download_fb_reel(r["reel_id"], fr_token, tmp)
            url = rp.supabase_upload(tmp, bucket, fn, sb_url, sb_key)
            print(f"[seed] #{r['n']} OK -> {url}")
            done += 1
        except Exception as e:  # noqa: BLE001
            print(f"[seed] #{r['n']} ERROR: {e}")
            fail += 1
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    print(f"\n[seed] subidos={done} omitidos={skip} fallos={fail} (total únicos={len(reels)})")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
