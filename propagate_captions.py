#!/usr/bin/env python3
"""Propaga la edición de un caption a los DEMÁS idiomas del mismo post (IA de Claude).

Lee state/propagate_request.json = {"image_url","platform","source_lang"} (lo escribe
el panel). Toma el caption editado del idioma fuente, EXTRAE el cuerpo (quita CTA,
enlaces y hashtags), lo TRADUCE a cada idioma que comparte el mismo image_url, y
RE-ENSAMBLA el caption con la CTA + enlaces + hashtags CORRECTOS de cada idioma.
También re-ensambla el idioma fuente para mantener IG y FB coherentes.

Idiomas: los ejercicios/artículos de ppf11 comparten image_url entre es/en/de/it/nl/pt
(mismo contenido traducido) -> se propagan entre ellos. fr es contenido propio (image_url
distinto) -> no tiene equivalentes, no se propaga.

Requiere ANTHROPIC_API_KEY. Al terminar, vacía la petición.
"""
import csv
import json
import os
import re
import sys

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("TRANSLATE_MODEL", "claude-sonnet-5")
LANG_NAME = {"es": "Spanish", "en": "English", "fr": "French", "de": "German",
             "it": "Italian", "pt": "Brazilian Portuguese", "nl": "Dutch"}

ROOT = os.path.dirname(os.path.abspath(__file__))
def _p(*a): return os.path.join(ROOT, *a)
def _load(rel):
    with open(_p(*rel.split("/")), encoding="utf-8-sig") as f: return json.load(f)

LINKS = _load("config/links.json")["free_exercises"]
CTA = _load("config/cta.json")
HASH = _load("config/hashtags.json")            # { idioma: hashtags base }
THEMES = _load("config/hashtags_themes.json")   # { categoria: { idioma: trio } }


def tags(lang, topic):
    return f"{HASH.get(lang, '').strip()} {(topic or '').strip()}".strip()


def cat_of(image_url):
    """Categoria del ejercicio: .../exercises/<marca>/<categoria>/... ('' si no casa)."""
    m = re.search(r"exercises/[^/]+/([a-z-]+)/", image_url or "")
    return m.group(1) if m else ""


def variant_idx(image_url, n):
    """Indice determinista 0..n-1 (mismo calculo que tools/assemble_captions.js)."""
    if not n:
        return 0
    return sum(ord(c) for c in str(image_url)) % n


def ex_tags(lang, cat):
    """Hashtags de EJERCICIO = base del idioma + trio tecnico de la categoria."""
    trio = (THEMES.get(cat, {}) or {}).get(lang, "")
    return " ".join(f"{HASH.get(lang, '').strip()} {trio.strip()}".strip().split())


def body_of(caption):
    """Cuerpo = el caption sin los DOS ultimos bloques (CTA y hashtags), separados por
    linea en blanco. Robusto ante cualquier texto de CTA (ya no depende del '👉').
    El cuerpo puede tener varios '\\n\\n' internos; CTA y hashtags son 1 bloque cada uno."""
    c = (caption or "").strip()
    parts = c.split("\n\n")
    if len(parts) >= 3:
        return "\n\n".join(parts[:-2]).strip()
    # fallback: primer bloque antes de un marcador de CTA/hashtags
    return re.split(r"\n\n(?:👉|🔖|#)", c, maxsplit=1)[0].strip()


def assemble(kind, lang, body, topic, url, image_url):
    free_ex = LINKS.get(lang, "")
    if kind == "exercises":
        ht = ex_tags(lang, cat_of(image_url))
        ig_arr = CTA['exercise']['ig'].get(lang, [])
        if isinstance(ig_arr, list):
            ig_cta = ig_arr[variant_idx(image_url, len(ig_arr))] if ig_arr else ""
        else:  # compatibilidad con formato antiguo (string)
            ig_cta = ig_arr
        ig = f"{body}\n\n{ig_cta}\n\n{ht}"
        fb_cta = CTA['exercise']['fb'].get(lang, '').replace("{free_ex}", free_ex).replace("{exercise_url}", url)
        fb = f"{body}\n\n{fb_cta}\n\n{ht}"
        return ig, fb
    ht = tags(lang, topic)  # articulos: base + tag de tema del CSV (sin cambios)
    fb_cta = CTA['article']['fb'].get(lang, '').replace("{article_url}", url).replace("{free_ex}", free_ex)
    return "", f"{body}\n\n{fb_cta}\n\n{ht}"


def translate_body(api_key, src_body, tgt):
    system = ("You are an elite football (soccer) physical-preparation coach and native copywriter. "
              "You translate the descriptive BODY of a social caption, natively and idiomatically, into the target language, "
              "with correct football terminology. Keep the ⚽ opening, the emojis, the 🎯 line if present, tuteo, and the same "
              "line structure. Do NOT add any URL, hashtag or call-to-action. Output ONLY the translated body, nothing else.")
    user = f"Target language: {LANG_NAME.get(tgt, tgt)} ({tgt}).\n\nBody to translate:\n{src_body}"
    r = requests.post(API_URL, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                      "content-type": "application/json"},
                      json={"model": MODEL, "max_tokens": 500, "system": system,
                            "messages": [{"role": "user", "content": user}]}, timeout=90)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["content"][0]["text"].strip()


def read_csv(name):
    with open(_p("content", name), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, (list(rows[0].keys()) if rows else [])


def write_csv(name, rows, fields):
    with open(_p("content", name), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(rows)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: falta ANTHROPIC_API_KEY", file=sys.stderr); sys.exit(2)
    try:
        req = _load("state/propagate_request.json")
    except Exception:
        req = {}
    img, src = req.get("image_url"), req.get("source_lang")
    platform = req.get("platform", "fb")
    if not img or not src:
        print("Sin petición de propagación."); return

    for kind, name in (("exercises", "exercises.csv"), ("articles", "articles.csv")):
        rows, fields = read_csv(name)
        srow = next((r for r in rows if r["language"] == src and r["image_url"] == img), None)
        if not srow:
            continue
        src_caption = srow.get("caption_ig") if (kind == "exercises" and platform == "ig") else srow.get("caption_fb")
        src_body = body_of(src_caption or srow.get("caption_fb") or srow.get("caption_ig"))
        # 1) re-ensamblar el idioma fuente (coherencia ig/fb)
        ig, fb = assemble(kind, src, src_body, srow.get("hashtags", ""), srow.get("url", ""), img)
        if kind == "exercises": srow["caption_ig"] = ig
        srow["caption_fb"] = fb
        # 2) traducir a los idiomas que comparten el mismo post (mismo image_url)
        targets = [r for r in rows if r["image_url"] == img and r["language"] != src]
        ok, fail = 0, 0
        for r in targets:
            tgt = r["language"]
            try:
                tbody = translate_body(api_key, src_body, tgt)
                ig, fb = assemble(kind, tgt, tbody, r.get("hashtags", ""), r.get("url", ""), img)
                if kind == "exercises": r["caption_ig"] = ig
                r["caption_fb"] = fb
                print(f"[{tgt}] propagado")
                ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"[{tgt}] ERROR: {e}", file=sys.stderr); fail += 1
        write_csv(name, rows, fields)
        print(f"Propagación {kind}: {ok} idiomas OK, {fail} fallidos.")
        break
    else:
        print(f"No se encontró el post {img} en idioma {src}.", file=sys.stderr)

    # vaciar la petición
    with open(_p("state", "propagate_request.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)


if __name__ == "__main__":
    main()
