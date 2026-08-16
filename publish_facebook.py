#!/usr/bin/env python3
"""Pipeline de FACEBOOK.

Publica UN post en cada Pagina (7 idiomas) del tipo indicado.
  python publish_facebook.py --type article    # horario A
  python publish_facebook.py --type exercise   # horario B

Usa --dry-run para simular sin publicar.
"""
import argparse
import random
import re
import sys
import time

import requests

from src.config import FB_HOST, get_token, load_accounts, load_templates
from src.content import load_items, render_caption
from src.facebook import publish_comment, publish_photo
from src import state as st

KIND_BY_TYPE = {"article": "articles", "exercise": "exercises"}

# --- ANTI-FILTRO DE SPAM DE FACEBOOK (auditoria 03-08-2026) ---
# Evidencia: posts manuales en la MISMA pagina = 5-13K de alcance; los del sistema = 0-2.
# Causas: (a) foto por API con ENLACE en el caption -> FB la entierra; (b) las 7 paginas
# publicando la MISMA imagen en el MISMO minuto -> filtro de contenido duplicado.
# Arreglo: los enlaces van al PRIMER COMENTARIO (el caption solo lo anuncia) y se
# publica con desfase de 3-5 min entre paginas.
LINK_RE = re.compile(r"https?://\S+|www\.\S+")
LINKS_IN_COMMENT = {
    "es": "👇 Enlaces en el primer comentario",
    "en": "👇 Links in the first comment",
    "fr": "👇 Liens dans le premier commentaire",
    "de": "👇 Links im ersten Kommentar",
    "it": "👇 Link nel primo commento",
    "pt": "👇 Links no primeiro comentário",
    "nl": "👇 Links in de eerste reactie",
}
STAGGER_RANGE = (180, 300)  # segundos entre paginas (3-5 min)


def split_links(caption, lang):
    """Devuelve (caption_sin_enlaces, texto_del_comentario|None).

    Las lineas del caption que contienen un enlace pasan enteras al comentario
    (conservan su texto de contexto, p.ej. '👉 Lee el articulo completo: URL').
    """
    keep, linked = [], []
    for ln in caption.split("\n"):
        (linked if LINK_RE.search(ln) else keep).append(ln)
    if not linked:
        return caption, None
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip()
    pointer = LINKS_IN_COMMENT.get(lang, LINKS_IN_COMMENT["en"])
    return body + "\n\n" + pointer, "\n".join(linked)


_CAN_COMMENT = {}


def can_comment(token):
    """True si el token puede comentar como Pagina (permiso pages_manage_engagement).

    AUDITORIA 16-08-2026: NINGUNO de los 7 tokens tenia ese permiso, asi que
    publish_comment fallaba SIEMPRE y los 267 posts publicados desde el 03-08
    anunciaban "Enlaces en el primer comentario" sin que existiera comentario
    alguno (y sin enlace en el caption, porque split_links lo habia sacado).
    El fallo paso desapercibido 13 dias porque se capturaba como simple aviso.

    Ante la duda (fallo de red, respuesta inesperada) devolvemos False: es mucho
    mejor dejar el enlace DENTRO del caption que prometer un comentario que no
    va a existir.
    """
    if token in _CAN_COMMENT:
        return _CAN_COMMENT[token]
    ok = False
    try:
        resp = requests.get(
            f"{FB_HOST}/debug_token",
            params={"input_token": token, "access_token": token},
            timeout=20,
        )
        if resp.status_code == 200:
            scopes = (resp.json().get("data") or {}).get("scopes") or []
            ok = "pages_manage_engagement" in scopes
    except Exception:  # noqa: BLE001 (sin permiso confirmado -> tratamos como que no)
        ok = False
    _CAN_COMMENT[token] = ok
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=list(KIND_BY_TYPE), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="publicar solo este idioma (p.ej. es)")
    parser.add_argument("--force", action="store_true", help="publicar aunque ya se hiciera hoy")
    args = parser.parse_args()

    slot = f"fb:{args.type}"
    if not args.dry_run and not args.force and st.already_published(slot):
        print(f"[FB] {slot} ya publicado hoy (Paris); se omite (idempotencia).")
        return

    kind = KIND_BY_TYPE[args.type]
    accounts = load_accounts()
    templates = load_templates()
    state = st.load_state()

    ok, fail = 0, 0
    published_any = False
    used_images = set()  # ninguna Pagina repite la imagen de otra en esta ejecucion
    for lang, cfg in accounts["languages"].items():
        if args.only and lang != args.only:
            continue
        if not cfg.get("enabled", True):
            print(f"[FB][{lang}] pausado (enabled=false); se omite.")
            continue
        fb = cfg.get("facebook")
        if not fb:
            continue
        # DESFASE anti-duplicados: no publicar las 7 paginas en el mismo minuto.
        if published_any and not args.dry_run:
            pause = random.uniform(*STAGGER_RANGE)
            print(f"[FB] desfase anti-spam: {pause/60:.1f} min antes de '{lang}'…")
            time.sleep(pause)
        items = load_items(kind, lang)
        if not items:
            print(f"[FB][{lang}] sin contenido de tipo '{kind}'")
            continue
        # cada Pagina recorre el catalogo en su propio orden (ver src/state.py)
        items = st.order_for_language(items, lang)
        key = f"fb:{lang}:{kind}"
        item = st.pick_next(items, key, state, exclude=used_images)
        used_images.add(item["image_url"])
        # Preferimos el caption ya redactado (columna caption_fb); si no, plantilla.
        caption = (item.get("caption_fb") or "").strip()
        if not caption:
            try:
                template = templates[args.type][lang]
            except KeyError:
                print(f"[FB][{lang}] falta caption_fb y plantilla '{args.type}'")
                fail += 1
                continue
            caption = render_caption(template, item)

        if args.dry_run:
            print(f"[FB][{lang}] DRY-RUN -> {item['url']}\n{caption}\n---")
            st.mark_posted(state, key, item["image_url"])
            ok += 1
            continue
        hist = {"platform": "fb", "lang": lang, "type": args.type,
                "title": item.get("title", ""), "url": item.get("url", ""),
                "image_url": item["image_url"]}
        try:
            token = get_token(f"FB_TOKEN_{lang.upper()}")
            # Enlaces FUERA del caption (al primer comentario) SOLO si de verdad
            # podemos comentar; si no, se quedan en el caption (ver can_comment).
            if can_comment(token):
                caption_fb, comment_text = split_links(caption, lang)
            else:
                caption_fb, comment_text = caption, None
                print(f"[FB][{lang}] AVISO: al token le falta 'pages_manage_engagement'; "
                      f"los enlaces se quedan DENTRO del caption")
            res = publish_photo(fb["page_id"], token, item["image_url"], caption_fb)
            print(f"[FB][{lang}] OK id={res.get('id')} <- {item['url']}")
            comment_status = "en_caption" if comment_text is None else "pendiente"
            if comment_text:
                target = res.get("post_id") or res.get("id")
                try:
                    publish_comment(target, token, comment_text)
                    comment_status = "ok"
                    print(f"[FB][{lang}] enlaces publicados en el primer comentario")
                except Exception as ce:  # noqa: BLE001 (el post ya salio, pero esto NO puede pasar en silencio)
                    comment_status = "fallo"
                    print(f"[FB][{lang}] ERROR: el post salio pero el comentario con los "
                          f"enlaces fallo (el caption los promete): {ce}")
                    fail += 1
            st.mark_posted(state, key, item["image_url"])
            st.log_history({**hist, "status": "ok", "post_id": res.get("id", ""),
                            "comment": comment_status})
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FB][{lang}] ERROR: {e}")
            st.log_history({**hist, "status": "error", "error": str(e)[:200]})
            fail += 1
        published_any = True

    # OJO: en dry-run NO se persiste. Antes se guardaba siempre, asi que una
    # simulacion adelantaba la rotacion real y el siguiente disparo se saltaba
    # los ejercicios "publicados" en la simulacion.
    if not args.dry_run:
        st.save_state(state)
    if ok and not args.dry_run:
        st.mark_published(slot)
    print(f"[FB] terminado type={args.type} ok={ok} fail={fail}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
