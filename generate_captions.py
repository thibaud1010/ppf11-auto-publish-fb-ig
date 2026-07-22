#!/usr/bin/env python3
"""Redactor de captions con IA (pre-generacion).

En vez de una plantilla plana, un "copywriter" experto en preparacion fisica de
futbol ESCRIBE cada caption, nativo en su idioma, con terminologia futbolistica
correcta, un hook potente y respetando el tono del contenido. Se guarda en el CSV
(columnas caption_ig / caption_fb) para revisarlo y publicar sin depender de la API.

Uso:
  ANTHROPIC_API_KEY=... python generate_captions.py --kind exercises --sample 1
  python generate_captions.py --kind exercises            # todas las filas
  python generate_captions.py --kind articles --only es   # solo un idioma

Lee content/<kind>_enriched.csv si existe (con description/category); si no, el
content/<kind>.csv normal. Escribe de vuelta el mismo fichero con caption_ig/caption_fb.
"""
import argparse
import csv
import os
import sys

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("CAPTION_MODEL", "claude-sonnet-5")

LANG_NAME = {
    "es": "Spanish", "en": "English", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Brazilian Portuguese", "nl": "Dutch",
}
ROOT = os.path.dirname(os.path.abspath(__file__))

SYSTEM = """You are an elite football (soccer) physical-preparation coach AND a social-media copywriter for the brand PPF11. You write ONE caption, natively, in the requested language.

NON-NEGOTIABLE QUALITY BAR:
- Write natively in the target language with CORRECT, natural football terminology (the words a real coach in that country would use). Never a literal/word-for-word translation.
- Substance, not filler: a hook that makes a coach or player stop scrolling, then the real value — what this exercise/article trains, why it matters on the pitch. Make them want to read.
- MATCH THE TONE of the source material: precise and technical for a drill; motivating and reflective for a mindset/planning article. Never generic.
- Concise and scannable: about 45-90 words. You may use 1-2 short line breaks and at most 1-2 tasteful emojis (only if they fit the tone). No walls of text.
- End with a natural call to action:
   * Instagram -> invite them to get the full free exercise via the link in bio (say it naturally in the language; do NOT paste any URL).
   * Facebook -> invite them to read/train via the link (a real URL will be appended after your text, so end with a natural lead-in, do NOT write the URL yourself).
- Do NOT include hashtags (they are added separately).
- Do NOT invent facts, numbers or claims beyond the material given. Stay faithful to it.
- Output ONLY the caption text. No quotes, no preamble, no notes."""


def write_caption(api_key, lang, platform, material):
    plat = "Instagram (feed, NO clickable links)" if platform == "ig" else "Facebook (a link will follow)"
    user = (
        f"Target language: {LANG_NAME.get(lang, lang)} ({lang}).\n"
        f"Platform: {plat}.\n\n"
        f"Source material (write the caption from this, faithfully):\n"
        f"- Title: {material.get('title','')}\n"
        f"- Objective/summary: {material.get('summary','')}\n"
        f"- Full description: {material.get('description','')}\n"
        f"- Category/topic: {material.get('category','')}\n"
    )
    r = requests.post(
        API_URL,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 400, "system": SYSTEM,
              "messages": [{"role": "user", "content": user}]},
        timeout=90,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["content"][0]["text"].strip()


def csv_path(kind):
    enriched = os.path.join(ROOT, "content", f"{kind}_enriched.csv")
    return enriched if os.path.exists(enriched) else os.path.join(ROOT, "content", f"{kind}.csv")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["exercises", "articles"], required=True)
    p.add_argument("--sample", type=int, default=0, help="genera solo N items por idioma (0 = todos)")
    p.add_argument("--only", default="", help="solo este idioma")
    args = p.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: falta ANTHROPIC_API_KEY", file=sys.stderr)
        sys.exit(2)

    path = csv_path(args.kind)
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys()) if rows else []
    for col in ("caption_ig", "caption_fb"):
        if col not in fields:
            fields.append(col)

    # cuantos por idioma llevamos (para --sample)
    per_lang = {}
    ok, fail = 0, 0
    for row in rows:
        lang = (row.get("language") or "").strip().lower()
        if args.only and lang != args.only:
            continue
        if args.sample:
            per_lang[lang] = per_lang.get(lang, 0)
            if per_lang[lang] >= args.sample:
                continue
            per_lang[lang] += 1
        mat = {k: (row.get(k) or "").strip() for k in ("title", "summary", "description", "category")}
        try:
            row["caption_fb"] = write_caption(api_key, lang, "fb", mat)
            if args.kind == "exercises":  # los ejercicios tambien van a IG
                row["caption_ig"] = write_caption(api_key, lang, "ig", mat)
            print(f"[{lang}] OK :: {mat['title'][:50]}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[{lang}] ERROR :: {mat['title'][:40]} -> {e}", file=sys.stderr)
            fail += 1

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)

    print(f"Generados: {ok}  Fallidos: {fail}  -> {os.path.basename(path)}")
    sys.exit(1 if ok == 0 else 0)


if __name__ == "__main__":
    main()
