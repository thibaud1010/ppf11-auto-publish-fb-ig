#!/usr/bin/env python3
"""Pipeline de INSTAGRAM.

Publica UN ejercicio en cada cuenta IG (7 cuentas). Se ejecuta en dos horarios
distintos; la rotacion asegura que cada ejecucion use un ejercicio diferente.
  python publish_instagram.py            # horario C y horario D
  python publish_instagram.py --dry-run
"""
import argparse
import sys

from src.config import FB_HOST, IG_LOGIN_HOST, get_token, load_accounts, load_templates
from src.content import load_items, render_caption
from src.instagram import publish
from src import state as st

KIND = "exercises"
TYPE = "ig_exercise"  # caption sin URL clicable (IG usa "link en bio")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="publicar solo este idioma (p.ej. es)")
    parser.add_argument("--force", action="store_true", help="publicar aunque ya se hiciera esta franja hoy")
    args = parser.parse_args()

    # franja segun la hora de Paris: mañana (<13h) o tarde
    slot = "ig:morning" if st.paris_now().hour < 13 else "ig:evening"
    if not args.dry_run and not args.force and st.already_published(slot):
        print(f"[IG] {slot} ya publicado hoy (Paris); se omite (idempotencia).")
        return

    accounts = load_accounts()
    templates = load_templates()
    state = st.load_state()

    ok, fail = 0, 0
    for lang, cfg in accounts["languages"].items():
        if args.only and lang != args.only:
            continue
        ig = cfg.get("instagram")
        if not ig:
            continue
        items = load_items(KIND, lang)
        if not items:
            print(f"[IG][{lang}] sin ejercicios")
            continue
        key = f"ig:{lang}:{KIND}"
        item = st.pick_next(items, key, state)
        # Preferimos el caption ya redactado (columna caption_ig); si no, plantilla.
        caption = (item.get("caption_ig") or "").strip()
        if not caption:
            try:
                template = templates[TYPE][lang]
            except KeyError:
                print(f"[IG][{lang}] falta caption_ig y plantilla '{TYPE}'")
                fail += 1
                continue
            caption = render_caption(template, item)

        if args.dry_run:
            print(f"[IG][{lang}] DRY-RUN -> {item['url']}\n{caption}\n---")
            st.mark_posted(state, key, item["image_url"])
            ok += 1
            continue
        try:
            # SISTEMA MIXTO: host + token segun instagram.mode de accounts.json
            mode = ig.get("mode", "page")
            if mode == "login":  # en/it/de/pt: Instagram Login
                host = IG_LOGIN_HOST
                token = get_token(f"IG_TOKEN_{lang.upper()}")
            else:  # "page" (es/fr/nl): IG vinculado a la Pagina -> token de la Pagina
                host = FB_HOST
                token = get_token(f"FB_TOKEN_{lang.upper()}")
            res = publish(ig["ig_user_id"], token, item["image_url"], caption, host=host)
            print(f"[IG][{lang}] OK ({mode}) id={res.get('id')} <- {item['url']}")
            st.mark_posted(state, key, item["image_url"])
            st.log_history({"platform": "ig", "lang": lang, "type": "exercise",
                            "title": item.get("title", ""), "url": item.get("url", ""),
                            "image_url": item["image_url"], "status": "ok", "post_id": res.get("id", "")})
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[IG][{lang}] ERROR: {e}")
            st.log_history({"platform": "ig", "lang": lang, "type": "exercise",
                            "title": item.get("title", ""), "url": item.get("url", ""),
                            "image_url": item.get("image_url", ""), "status": "error", "error": str(e)[:200]})
            fail += 1

    st.save_state(state)
    if ok and not args.dry_run:
        st.mark_published(slot)
    print(f"[IG] terminado ok={ok} fail={fail}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
