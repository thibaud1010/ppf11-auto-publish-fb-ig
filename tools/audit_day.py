"""Auditoria diaria de publicaciones (SOLO LECTURA: no publica ni borra nada).

Para un dia D (por defecto AYER, en la hora local de cada idioma) y cada idioma activo:
  1) QUE DEBIA SALIR  -> se deduce de config/accounts.json, los catalogos, config/reels.json
     (langs + start), tools/due.py (REELS_LANGS), max_cycles e ig_story.
  2) QUE DICE EL SISTEMA -> state/history.jsonl (ok / error) y state/published.json
     (marca de franja: si esta marcada y no hay 'ok' = se intento y fallo; si no esta
     marcada = el disparo NUNCA llego a lanzarse).
  3) QUE HAY DE VERDAD EN META -> cada post_id existe; los videos de FB no quedaron en
     error; y en IG se cuentan los posts del dia en la cuenta (si Meta tiene MAS que
     nuestro registro = posible duplicado o post 'fallido' que si salio).

Uso:
  python tools/audit_day.py                 # ayer
  python tools/audit_day.py --date 2026-11-26
  python tools/audit_day.py --issue         # ademas abre un aviso (Issue) en GitHub si hay problemas
Salida: state/audit/<D>.json + state/audit/<D>.md
"""
import argparse
import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.config import load_accounts, get_token, FB_HOST, IG_LOGIN_HOST  # noqa: E402
from src.content import load_items  # noqa: E402
from src import exercise_videos as ev  # noqa: E402
from src import schedule as sch  # noqa: E402
from tools.due import REELS_LANGS  # noqa: E402

STATE = os.path.join(ROOT, "state")
STORY_LOG_SINCE = "2026-11-27"   # antes de esta fecha las stories no se registraban
ASSIGNEE = "thibaud1010"
NOMBRE = {("fb", "article"): "FB articulo", ("fb", "exercise"): "FB ejercicio (video)",
          ("ig", "exercise"): "IG ejercicio (reel)", ("ig", "reel"): "IG reel del dia",
          ("fb", "reel"): "FB reel del dia", ("ig", "story"): "IG story"}


def tz_of(lang):
    return ZoneInfo(sch._lang_cfg(sch._config(), lang)["tz"])


def local_day(ts, lang):
    t = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    return t.astimezone(tz_of(lang)).strftime("%Y-%m-%d")


def expected(lang, cfg, day, reels_cfg, state):
    """Lista de (plataforma, tipo) que debian salir ese dia."""
    exp = []
    if cfg.get("facebook"):
        try:
            if load_items("articles", lang):
                exp.append(("fb", "article"))
        except FileNotFoundError:
            pass
    vids = ev.load(lang)
    if vids:
        if cfg.get("facebook") and not ev.cycles_exhausted(cfg, state, "fb", lang, len(vids)):
            exp.append(("fb", "exercise"))
        if cfg.get("instagram") and not ev.cycles_exhausted(cfg, state, "ig", lang, len(vids)):
            exp.append(("ig", "exercise"))
    start = (reels_cfg.get("start") or {}).get(lang)
    if (lang in reels_cfg.get("langs", []) and lang in REELS_LANGS and cfg.get("instagram")
            and (not start or day >= start)):
        exp.append(("ig", "reel"))
        if cfg.get("reels_fb_api"):
            exp.append(("fb", "reel"))
    return exp


SLOT = {("fb", "article"): "fb:article", ("fb", "exercise"): "fb:exercise",
        ("ig", "exercise"): "ig:morning", ("ig", "reel"): "reels", ("fb", "reel"): "reels"}


def graph(host, path, token, **params):
    try:
        r = requests.get(f"{host}/{path}", params={**params, "access_token": token}, timeout=30)
        return r.json() if r.content else {}
    except Exception as e:  # noqa: BLE001
        return {"error": {"message": str(e)}}


def meta_checks(lang, cfg, day, rows, problems, info):
    """Comprueba en Meta los post_id del dia + cuenta los posts de IG del dia."""
    ig = cfg.get("instagram") or {}
    try:
        fb_token = get_token(f"FB_TOKEN_{lang.upper()}")
    except RuntimeError:
        fb_token = None
    if ig.get("mode") == "login":
        ig_host = IG_LOGIN_HOST
        try:
            ig_token = get_token(f"IG_TOKEN_{lang.upper()}")
        except RuntimeError:
            ig_token = None
    else:
        ig_host, ig_token = FB_HOST, fb_token

    for r in rows:
        if r.get("status") != "ok" or not r.get("post_id"):
            continue
        name = NOMBRE.get((r["platform"], r["type"]), r["type"])
        if r["platform"] == "ig":
            if not ig_token or r["type"] == "story":   # las stories caducan a las 24 h: no se comprueban
                continue
            d = graph(ig_host, r["post_id"], ig_token, fields="id,permalink")
            if "error" in d:
                problems.append(f"{name}: el post {r['post_id']} NO aparece en Meta ({d['error'].get('message', '')[:120]})")
            else:
                info.append(f"{name}: {d.get('permalink', r['post_id'])}")
        else:
            if not fb_token:
                continue
            d = graph(FB_HOST, r["post_id"], fb_token, fields="id")
            if "error" in d:
                problems.append(f"{name}: el post {r['post_id']} NO aparece en Meta ({d['error'].get('message', '')[:120]})")
                continue
            if r["type"] in ("exercise", "reel"):
                v = graph(FB_HOST, r["post_id"], fb_token, fields="status")
                vs = ((v.get("status") or {}).get("video_status") or "") if "error" not in v else ""
                if vs in ("error", "expired"):
                    problems.append(f"{name}: el video {r['post_id']} quedo en estado '{vs}' en Facebook")
            info.append(f"{name}: facebook.com/{r['post_id']}")

    # Recuento de IG: Meta vs nuestro registro (reels de ejercicio + reel del dia)
    if ig_token and ig.get("ig_user_id"):
        d = graph(ig_host, f"{ig['ig_user_id']}/media", ig_token, fields="id,timestamp", limit=25)
        if "error" in d:
            problems.append(f"IG: no se pudo leer la cuenta para contar posts ({d['error'].get('message', '')[:120]})")
        else:
            tz = tz_of(lang)
            n_meta = sum(1 for m in d.get("data", [])
                         if datetime.datetime.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
                         .replace(tzinfo=datetime.timezone.utc).astimezone(tz).strftime("%Y-%m-%d") == day)
            n_log = sum(1 for r in rows if r["platform"] == "ig" and r["type"] in ("exercise", "reel")
                        and r.get("status") == "ok")
            if n_meta > n_log:
                problems.append(f"IG: la cuenta tiene {n_meta} posts ese dia y el registro solo {n_log} "
                                f"-> posible DUPLICADO o un post marcado como fallido que si salio")


def audit(day):
    accounts = load_accounts()["languages"]
    with open(os.path.join(ROOT, "config", "reels.json"), encoding="utf-8") as f:
        reels_cfg = json.load(f)
    with open(os.path.join(STATE, "posted_log.json"), encoding="utf-8") as f:
        state = json.load(f)
    with open(os.path.join(STATE, "published.json"), encoding="utf-8") as f:
        marks = json.load(f)
    hist = []
    with open(os.path.join(STATE, "history.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                hist.append(json.loads(line))

    report = {"date": day, "langs": {}, "total_problems": 0}
    for lang, cfg in accounts.items():
        if not cfg.get("enabled", True):
            continue
        rows = [r for r in hist if r.get("lang") == lang and local_day(r["ts"], lang) == day]
        problems, info = [], []
        for plat, typ in expected(lang, cfg, day, reels_cfg, state):
            oks = [r for r in rows if r["platform"] == plat and r["type"] == typ and r["status"] == "ok"]
            errs = [r for r in rows if r["platform"] == plat and r["type"] == typ and r["status"] == "error"]
            name = NOMBRE[(plat, typ)]
            if not oks:
                marked = f"{day}:{SLOT[(plat, typ)]}:{lang}" in marks
                if errs:
                    problems.append(f"{name}: FALLO -> {errs[-1].get('error', '')[:160]}")
                elif marked:
                    problems.append(f"{name}: NO salio (la franja se lanzo pero no hay registro de exito)")
                else:
                    problems.append(f"{name}: NO salio (la publicacion nunca se lanzo ese dia)")
            elif len(oks) > 1:
                problems.append(f"{name}: DUPLICADO ({len(oks)} publicaciones: "
                                + ", ".join(r.get('post_id', '?') for r in oks) + ")")
            elif errs:
                info.append(f"{name}: hubo {len(errs)} error(es) antes de salir bien")
        for r in rows:
            if r["platform"] == "fb" and r.get("comment") == "fallo":
                problems.append(f"{NOMBRE.get((r['platform'], r['type']), r['type'])}: "
                                f"el comentario con los enlaces NO se publico (post {r.get('post_id')})")
        if cfg.get("ig_story") and day >= STORY_LOG_SINCE:
            n_ig = sum(1 for r in rows if r["platform"] == "ig" and r["type"] in ("exercise", "reel")
                       and r["status"] == "ok")
            n_story = sum(1 for r in rows if r["platform"] == "ig" and r["type"] == "story" and r["status"] == "ok")
            if n_story < n_ig:
                err = [r.get("error", "") for r in rows if r["type"] == "story" and r["status"] == "error"]
                problems.append(f"IG story: {n_story} de {n_ig}" + (f" -> {err[-1][:140]}" if err else ""))
        meta_checks(lang, cfg, day, rows, problems, info)
        report["langs"][lang] = {"problems": problems, "info": info,
                                 "posts_ok": sum(1 for r in rows if r["status"] == "ok")}
        report["total_problems"] += len(problems)
    return report


def to_markdown(rep):
    out = [f"## Auditoria de publicaciones del {rep['date']}", ""]
    bad = {l: v for l, v in rep["langs"].items() if v["problems"]}
    good = [l for l, v in rep["langs"].items() if not v["problems"]]
    out.append(f"**{rep['total_problems']} problema(s)** en {len(bad)} idioma(s). "
               f"Sin problemas: {', '.join(good) or 'ninguno'}.")
    out.append("")
    for l, v in bad.items():
        out.append(f"### {l} ({v['posts_ok']} publicaciones OK)")
        out += [f"- ❌ {p}" for p in v["problems"]]
        out.append("")
    out.append("<details><summary>Detalle de lo publicado</summary>\n")
    for l, v in rep["langs"].items():
        out.append(f"**{l}**")
        out += [f"- {i}" for i in v["info"]] or ["- (nada)"]
    out.append("\n</details>")
    out.append("\n_Generado por tools/audit_day.py (solo lectura)._")
    return "\n".join(out)


def open_issue(rep, md):
    repo, tok = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo or not tok:
        print("[AUDIT] sin GITHUB_REPOSITORY/GITHUB_TOKEN: no se abre aviso")
        return
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    title = f"Auditoria {rep['date']}: {rep['total_problems']} problema(s) de publicacion"
    r = requests.post(f"https://api.github.com/repos/{repo}/issues", headers=h, timeout=30,
                      json={"title": title, "body": md, "assignees": [ASSIGNEE], "labels": ["auditoria"]})
    print(f"[AUDIT] aviso GitHub: {r.status_code} {r.json().get('html_url', r.text[:200])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (por defecto ayer, hora de Paris)")
    ap.add_argument("--issue", action="store_true", help="abrir aviso en GitHub si hay problemas")
    a = ap.parse_args()
    day = a.date or (datetime.datetime.now(ZoneInfo("Europe/Paris")) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    rep = audit(day)
    md = to_markdown(rep)
    os.makedirs(os.path.join(STATE, "audit"), exist_ok=True)
    with open(os.path.join(STATE, "audit", f"{day}.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    with open(os.path.join(STATE, "audit", f"{day}.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(md)
    if a.issue and rep["total_problems"]:
        open_issue(rep, md)


if __name__ == "__main__":
    main()
