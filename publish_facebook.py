#!/usr/bin/env python3
"""Pipeline de FACEBOOK.

Publica UN post en cada Pagina (7 idiomas) del tipo indicado.
  python publish_facebook.py --type article    # horario A
  python publish_facebook.py --type exercise   # horario B

Usa --dry-run para simular sin publicar.
"""
import argparse
import sys

from src.config import get_token, load_accounts, load_templates
from src.content import load_items, render_caption
from src.facebook import publish_photo
from src import state as st

KIND_BY_TYPE = {"article": "articles", "exercise": "exercises"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=list(KIND_BY_TYPE), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="publicar solo este idioma (p.ej. es)")
    args = parser.parse_args()

    kind = KIND_BY_TYPE[args.type]
    accounts = load_accounts()
    templates = load_templates()
    state = st.load_state()

    ok, fail = 0, 0
    for lang, cfg in accounts["languages"].items():
        if args.only and lang != args.only:
            continue
        fb = cfg.get("facebook")
        if not fb:
            continue
        items = load_items(kind, lang)
        if not items:
            print(f"[FB][{lang}] sin contenido de tipo '{kind}'")
            continue
        key = f"fb:{lang}:{kind}"
        item = st.pick_next(items, key, state)
        try:
            template = templates[args.type][lang]
        except KeyError:
            print(f"[FB][{lang}] falta plantilla '{args.type}' para el idioma")
            fail += 1
            continue
        caption = render_caption(template, item)

        if args.dry_run:
            print(f"[FB][{lang}] DRY-RUN -> {item['url']}\n{caption}\n---")
            st.mark_posted(state, key, item["image_url"])
            ok += 1
            continue
        try:
            token = get_token(f"FB_TOKEN_{lang.upper()}")
            res = publish_photo(fb["page_id"], token, item["image_url"], caption)
            print(f"[FB][{lang}] OK id={res.get('id')} <- {item['url']}")
            st.mark_posted(state, key, item["image_url"])
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FB][{lang}] ERROR: {e}")
            fail += 1

    st.save_state(state)
    print(f"[FB] terminado type={args.type} ok={ok} fail={fail}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
