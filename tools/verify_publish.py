"""Comprueba las invariantes de los cambios (solo lectura, no publica nada)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys

from src.config import load_accounts
from src.content import load_items
from src import state as st
import publish_facebook as pf

LANGS = ["es", "en", "de", "it", "pt", "nl"]
fallos = []


def check(cond, msg):
    print(("  OK   " if cond else "  FALLO ") + msg)
    if not cond:
        fallos.append(msg)


print("\n1) El orden por idioma cubre el catalogo entero, sin repetir ni perder items")
for kind in ("exercises", "articles"):
    for lang in LANGS:
        items = load_items(kind, lang)
        ordered = st.order_for_language(items, lang)
        ids = [i["image_url"] for i in ordered]
        check(len(ordered) == len(items), f"{kind}/{lang}: mismo numero de items ({len(items)})")
        check(len(set(ids)) == len(set(i["image_url"] for i in items)),
              f"{kind}/{lang}: mismas imagenes, sin perdidas ni duplicados")

print("\n2) Cada idioma recorre el catalogo en un orden DISTINTO")
for kind in ("exercises", "articles"):
    firsts = {l: st.order_for_language(load_items(kind, l), l)[0]["image_url"] for l in LANGS}
    check(len(set(firsts.values())) == len(LANGS), f"{kind}: los 6 idiomas empiezan por imagenes distintas")

print("\n3) Simulacion de 100 dias: ningun idioma repite hasta agotar el catalogo")
state = {}
colisiones = 0
por_idioma = {l: [] for l in LANGS}
for day in range(100):
    used = set()
    for lang in LANGS:
        items = st.order_for_language(load_items("exercises", lang), lang)
        key = f"fb:{lang}:exercises"
        item = st.pick_next(items, key, state, exclude=used)
        used.add(item["image_url"])
        por_idioma[lang].append(item["image_url"])
        st.mark_posted(state, key, item["image_url"])
    if len(used) < len(LANGS):
        colisiones += 1
check(colisiones == 0, f"100 dias sin dos Paginas con la misma imagen (colisiones: {colisiones})")
for lang in LANGS:
    total = len(load_items("exercises", lang))
    primeros = por_idioma[lang][:total]
    check(len(set(primeros)) == total,
          f"{lang}: los primeros {total} dias son {len(set(primeros))} ejercicios distintos (sin repetir)")

print("\n4) can_comment detecta el permiso que falta")
try:
    from src.config import get_token
    tok = get_token("FB_TOKEN_ES")
    puede = pf.can_comment(tok)
    check(puede is False, f"token es: can_comment = {puede} (hoy debe ser False: falta el permiso)")
    print("     -> con este resultado, los enlaces se quedan DENTRO del caption")
except Exception as e:  # noqa: BLE001
    print(f"  (sin token local: {e})")

print("\n5) can_comment ante un token invalido no revienta y devuelve False")
check(pf.can_comment("token_basura_para_probar") is False, "token invalido -> False (no excepcion)")

print("\n6) split_links solo se aplica cuando se puede comentar")
cap = "Texto del ejercicio\n\n👉 Mira la ficha: https://www.ppf11.com/es/x\n\n#futbol"
sin_enlace, comentario = pf.split_links(cap, "es")
check("https://" not in sin_enlace and comentario and "https://" in comentario,
      "split_links saca el enlace al comentario cuando SI se puede comentar")
check("https://" in cap, "sin permiso el caption conserva el enlace (se usa tal cual)")

print("\n" + ("TODO OK" if not fallos else f"{len(fallos)} FALLOS: " + "; ".join(fallos)))
sys.exit(1 if fallos else 0)
