#!/usr/bin/env python3
"""Genera un token de Instagram Login (60 dias) tras el OAuth de Instagram.

App: PPF Social Publish-IG (client_id 1143223668262484). Sirve para en/it/de/pt.

Pasos:
  1) Abre el enlace de autorizacion (te lo da Claude), loguea en la cuenta IG
     correcta (p.ej. @ppf11.it) y pulsa Autorizar.
  2) Instagram te redirige a la pagina del panel con  ...?code=XXXXX#_
     Copia el CODE: todo lo que va despues de  code=  y ANTES de  #_ .
  3) Ejecuta (el secreto va por variable de entorno, NO queda en el historial):
       Bash:        IG_APP_SECRET=xxxxx py tools/mint_ig_token.py --lang it --code "XXXXX"
       PowerShell:  $env:IG_APP_SECRET="xxxxx"; py tools/mint_ig_token.py --lang it --code "XXXXX"
  El secreto se saca de la app: Instagram -> API con conexion Instagram ->
  "Cle secrete Instagram" -> Afficher.

Escribe el token en config/secrets.json (IG_TOKEN_<LANG>, conservando el resto).
"""
import argparse
import json
import os
import sys

import requests

CLIENT_ID = "1143223668262484"
REDIRECT_URI = "https://thibaud1010.github.io/ppf11-auto-publish-fb-ig/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, help="idioma de la cuenta (en/it/de/pt)")
    ap.add_argument("--code", help="el code del redirect (sin el #_ final)")
    ap.add_argument("--url", help="la URL entera del redirect (se extrae el code sola)")
    args = ap.parse_args()

    secret = os.environ.get("IG_APP_SECRET")
    if not secret:
        sys.exit("Falta IG_APP_SECRET en el entorno (la clave secreta de la app de Instagram).")

    raw = args.code
    if not raw and args.url:
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(args.url).query)
        raw = (q.get("code") or [""])[0]
    if not raw:
        sys.exit("Falta --code o --url.")
    code = raw.split("#")[0].strip()  # Instagram anade un #_ al final

    # 1) code -> token corto (~1h)
    r = requests.post("https://api.instagram.com/oauth/access_token", timeout=30, data={
        "client_id": CLIENT_ID, "client_secret": secret,
        "grant_type": "authorization_code", "redirect_uri": REDIRECT_URI, "code": code})
    if r.status_code != 200:
        sys.exit(f"ERROR code->token corto {r.status_code}: {r.text[:300]}")
    short = r.json()["access_token"]

    # 2) token corto -> token largo (60 dias)
    l = requests.get("https://graph.instagram.com/access_token", timeout=30, params={
        "grant_type": "ig_exchange_token", "client_secret": secret, "access_token": short})
    if l.status_code != 200:
        sys.exit(f"ERROR corto->largo {l.status_code}: {l.text[:300]}")
    long_token = l.json()["access_token"]
    days = round(l.json().get("expires_in", 0) / 86400, 1)

    # 3) escribir en secrets.json conservando el resto
    p = os.path.join(ROOT, "config", "secrets.json")
    s = json.load(open(p, encoding="utf-8"))
    name = f"IG_TOKEN_{args.lang.upper()}"
    s[name] = long_token
    with open(p, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print(f"OK: {name} actualizado (expira en ~{days} dias).")
    print("Verifica con: node tools/check_tokens.js")


if __name__ == "__main__":
    main()
