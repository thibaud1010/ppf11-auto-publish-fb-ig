#!/usr/bin/env python3
"""Traduce plantillas y hashtags base de UN idioma fuente a los demas (IA de Claude).

Edita un idioma en el panel; este script propaga el cambio a los otros 6 traduciendo
SOLO el texto humano, conservando intactos:
  - los placeholders {title} {summary} {url} {hashtags}
  - los emojis y la estructura (saltos de linea)
  - la naturaleza de "hashtag" (localiza el tema, mantiene el #, sin espacios)

Uso:
  ANTHROPIC_API_KEY=... python translate_templates.py --source es
  python translate_templates.py --source es --targets en,fr --scope templates

Requiere la variable de entorno ANTHROPIC_API_KEY.
"""
import argparse
import json
import os
import sys

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("TRANSLATE_MODEL", "claude-haiku-4-5-20251001")
ALL_LANGS = ["es", "en", "fr", "de", "it", "pt", "nl"]
LANG_NAME = {
    "es": "Spanish", "en": "English", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese (Brazil)", "nl": "Dutch",
}
TEMPLATE_TYPES = ["article", "exercise", "ig_exercise"]

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(ROOT, "config", "templates.json")
HASHTAGS = os.path.join(ROOT, "config", "hashtags.json")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def call_claude(api_key, payload_desc, source_obj, target_lang):
    """Pide a Claude la version traducida (JSON) para un idioma destino."""
    system = (
        "You are a professional localizer for a football (soccer) physical-training brand. "
        "You translate short social-media caption templates and hashtag sets. "
        "STRICT RULES:\n"
        "1) Keep every placeholder EXACTLY as-is: {title} {summary} {url} {hashtags}. Do not translate or move them.\n"
        "2) Keep all emojis and the line-break structure identical.\n"
        "3) Translate ONLY the human-readable words into the target language, naturally and idiomatically.\n"
        "4) For hashtags: give natural, localized hashtags for the target language (not literal word-for-word). "
        "Keep the leading # and no spaces inside a tag. Keep the same number of hashtags.\n"
        "5) Return ONLY a JSON object with the same keys as the input, values translated. No commentary."
    )
    user = (
        f"Target language: {LANG_NAME[target_lang]} ({target_lang}).\n"
        f"{payload_desc}\n"
        f"Input JSON to translate:\n{json.dumps(source_obj, ensure_ascii=False, indent=2)}"
    )
    r = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 1500,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    # por si el modelo envuelve en ```json
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"): text.rfind("}") + 1]
    return json.loads(text)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="es", help="idioma fuente (por defecto es)")
    p.add_argument("--targets", default="", help="idiomas destino separados por coma (por defecto: todos menos el fuente)")
    p.add_argument("--scope", choices=["templates", "hashtags", "both"], default="both")
    args = p.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: falta ANTHROPIC_API_KEY", file=sys.stderr)
        sys.exit(2)

    src = args.source
    if src not in ALL_LANGS:
        print(f"ERROR: idioma fuente desconocido: {src}", file=sys.stderr)
        sys.exit(2)
    targets = [t for t in (args.targets.split(",") if args.targets else ALL_LANGS) if t and t != src]

    templates = _read(TEMPLATES)
    hashtags = _read(HASHTAGS)

    ok, fail = 0, 0
    for tgt in targets:
        try:
            if args.scope in ("templates", "both"):
                source_tpl = {t: templates[t][src] for t in TEMPLATE_TYPES if src in templates.get(t, {})}
                out = call_claude(api_key, "These are caption templates by type.", source_tpl, tgt)
                for t in TEMPLATE_TYPES:
                    if t in out and t in templates:
                        templates[t][tgt] = out[t]
            if args.scope in ("hashtags", "both"):
                src_tags = {"hashtags": hashtags.get(src, "")}
                out = call_claude(api_key, "This is a space-separated list of base hashtags.", src_tags, tgt)
                if "hashtags" in out:
                    hashtags[tgt] = out["hashtags"]
            print(f"[{tgt}] traducido desde {src}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[{tgt}] ERROR: {e}", file=sys.stderr)
            fail += 1

    if args.scope in ("templates", "both"):
        _write(TEMPLATES, templates)
    if args.scope in ("hashtags", "both"):
        _write(HASHTAGS, hashtags)

    print(f"Traducidos: {ok}  Fallidos: {fail}")
    sys.exit(1 if ok == 0 else 0)


if __name__ == "__main__":
    main()
