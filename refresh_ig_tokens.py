#!/usr/bin/env python3
"""Renueva los tokens de Instagram Login (60 dias) y vuelca el TOKENS_JSON actualizado.

Los tokens de las cuentas IG en modo "login" (en/it/de/pt) caducan a los 60 dias,
pero son renovables: cada renovacion los extiende otros 60 dias. Este script lee
TOKENS_JSON del entorno, renueva cada `IG_TOKEN_*` via
`graph.instagram.com/refresh_access_token`, y escribe el JSON COMPLETO (con los
`FB_TOKEN_*` intactos) al fichero indicado con --out.

Los tokens de Pagina de Facebook (FB_TOKEN_*) NO caducan y no se tocan.

Uso (en el workflow):
    python refresh_ig_tokens.py --out tokens.new.json
    gh secret set TOKENS_JSON < tokens.new.json
"""
import argparse
import json
import os
import sys

import requests

REFRESH_URL = "https://graph.instagram.com/refresh_access_token"


def refresh_one(token):
    r = requests.get(
        REFRESH_URL,
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data.get("expires_in")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="fichero de salida con el TOKENS_JSON renovado")
    args = parser.parse_args()

    raw = os.environ.get("TOKENS_JSON")
    if not raw:
        print("ERROR: falta la variable de entorno TOKENS_JSON", file=sys.stderr)
        sys.exit(2)
    tokens = json.loads(raw)

    ig_names = [n for n in tokens if n.startswith("IG_TOKEN_")]
    if not ig_names:
        print("No hay tokens IG_TOKEN_* que renovar.")

    changed, failed = 0, 0
    for name in ig_names:
        try:
            new_token, expires_in = refresh_one(tokens[name])
            tokens[name] = new_token
            days = round((expires_in or 0) / 86400, 1)
            print(f"{name}: renovado (expira en ~{days} dias)")
            changed += 1
        except Exception as e:  # noqa: BLE001
            print(f"{name}: ERROR al renovar -> {e}", file=sys.stderr)
            failed += 1

    # Escribe SIEMPRE el JSON completo (aunque algun IG fallara, conserva el resto).
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False)

    print(f"Renovados: {changed}  Fallidos: {failed}")
    # Si TODOS los IG fallaron, no reescribimos el secreto (evita romperlo).
    if ig_names and changed == 0:
        print("Ningun token IG se renovo; el secreto NO debe actualizarse.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
