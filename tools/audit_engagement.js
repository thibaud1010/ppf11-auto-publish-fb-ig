#!/usr/bin/env node
// Auditoria de likes/comentarios/alcance por idioma, a partir de state/history.jsonl.
//
// Consulta CADA publicacion por su ID en la Graph API (no estima nada) y saca la
// tabla por idioma y por tipo de contenido. Nacio de la auditoria del 16-08-2026,
// que descubrio que Facebook llevaba 267 posts con 1 solo like.
//
// Uso:
//   node tools/audit_engagement.js               (ultimos 30 dias)
//   node tools/audit_engagement.js --dias 60
//   node tools/audit_engagement.js --json salida.json
//
// Solo lectura: no publica ni borra nada. Necesita config/secrets.json o TOKENS_JSON.
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const V = process.env.GRAPH_VERSION || "v21.0";
const FB = `https://graph.facebook.com/${V}`;
const IGL = `https://graph.instagram.com/${V}`;
const CONCURRENCIA = 5;

const args = process.argv.slice(2);
const opt = (n, def) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : def; };
const DIAS = Number(opt("--dias", 30));
const JSON_OUT = opt("--json", null);

const tokens = (() => {
  const t = {};
  if (process.env.TOKENS_JSON) Object.assign(t, JSON.parse(process.env.TOKENS_JSON));
  const p = path.join(ROOT, "config/secrets.json");
  if (fs.existsSync(p)) Object.assign(t, JSON.parse(fs.readFileSync(p, "utf8")));
  return t;
})();
const accounts = JSON.parse(fs.readFileSync(path.join(ROOT, "config/accounts.json"), "utf8")).languages;

const desde = new Date(Date.now() - DIAS * 86400000).toISOString();
const historia = fs.readFileSync(path.join(ROOT, "state/history.jsonl"), "utf8")
  .trim().split("\n").map((l) => JSON.parse(l))
  .filter((r) => r.status === "ok" && r.post_id && r.ts >= desde);

async function api(url, params) {
  const u = new URL(url);
  for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  for (let i = 0; i < 3; i++) {
    try {
      const r = await fetch(u, { signal: AbortSignal.timeout(30000) });
      const j = await r.json().catch(() => ({}));
      if (r.ok) return j;
      const code = j?.error?.code;
      if ([4, 17, 32, 613].includes(code)) { await new Promise((s) => setTimeout(s, 5000 * (i + 1))); continue; }
      return { __error: j?.error?.message || `HTTP ${r.status}`, __code: code };
    } catch (e) {
      if (i === 2) return { __error: String(e.message || e) };
      await new Promise((s) => setTimeout(s, 2000));
    }
  }
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let i = 0;
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (i < items.length) { const k = i++; out[k] = await fn(items[k]); }
  }));
  return out;
}

async function metricasPost(rec) {
  const L = rec.lang.toUpperCase();
  const base = { ts: rec.ts, lang: rec.lang, platform: rec.platform, type: rec.type, post_id: rec.post_id };
  if (rec.platform === "fb") {
    const t = tokens[`FB_TOKEN_${L}`];
    if (!t) return { ...base, error: "sin token" };
    // el nodo foto y el nodo video admiten campos distintos -> de mas a menos
    let r = null;
    for (const fields of [
      "created_time,link,likes.summary(true).limit(0),comments.summary(true).limit(0),reactions.summary(true).limit(0)",
      "created_time,likes.summary(true).limit(0),comments.summary(true).limit(0)",
    ]) {
      r = await api(`${FB}/${rec.post_id}`, { fields, access_token: t });
      if (!r.__error || r.__code !== 100) break;
    }
    if (r.__error) return { ...base, error: r.__error };
    return {
      ...base,
      likes: r.reactions?.summary?.total_count ?? r.likes?.summary?.total_count ?? 0,
      comments: r.comments?.summary?.total_count ?? 0,
    };
  }
  const ig = accounts[rec.lang]?.instagram;
  if (!ig) return { ...base, error: "idioma sin cuenta IG" };
  const host = ig.mode === "page" ? FB : IGL;
  const t = ig.mode === "page" ? tokens[`FB_TOKEN_${L}`] : tokens[`IG_TOKEN_${L}`];
  if (!t) return { ...base, error: "sin token" };
  const r = await api(`${host}/${rec.post_id}`, {
    fields: "like_count,comments_count,media_product_type,permalink", access_token: t,
  });
  if (r.__error) return { ...base, error: r.__error };
  const fila = { ...base, likes: r.like_count ?? 0, comments: r.comments_count ?? 0, permalink: r.permalink || "" };
  // alcance: solo si la app tiene el permiso de insights (si no, se omite en silencio)
  const ins = await api(`${host}/${rec.post_id}/insights`, { metric: "reach", access_token: t });
  if (!ins.__error) fila.reach = ins.data?.[0]?.values?.[0]?.value ?? null;
  return fila;
}

const num = (x) => (x == null ? 0 : x);
const med = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
const f2 = (x) => (Math.round(x * 100) / 100).toFixed(2);

(async () => {
  console.log(`Auditando ${historia.length} publicaciones de los ultimos ${DIAS} dias...`);
  const filas = await mapLimit(historia, CONCURRENCIA, metricasPost);
  const ok = filas.filter((r) => !r.error);
  const langs = Object.keys(accounts);

  for (const plat of ["ig", "fb"]) {
    const dePlat = ok.filter((r) => r.platform === plat);
    if (!dePlat.length) continue;
    console.log(`\n=== ${plat.toUpperCase()} — por idioma ===`);
    console.log("lang | posts | likes | media | 0 likes | coment | alcance medio");
    for (const lang of langs) {
      const s = dePlat.filter((r) => r.lang === lang);
      if (!s.length) continue;
      const likes = s.map((r) => num(r.likes));
      const conReach = s.filter((r) => r.reach != null);
      console.log(
        [lang.padEnd(4), String(s.length).padStart(5),
         String(likes.reduce((a, b) => a + b, 0)).padStart(5),
         f2(med(likes)).padStart(5),
         `${likes.filter((x) => x === 0).length}`.padStart(7),
         String(s.reduce((a, r) => a + num(r.comments), 0)).padStart(6),
         conReach.length ? f2(med(conReach.map((r) => r.reach))).padStart(13) : "sin permiso".padStart(13),
        ].join(" | ")
      );
    }
    const likes = dePlat.map((r) => num(r.likes));
    console.log(`TOTAL: ${dePlat.length} posts, ${likes.reduce((a, b) => a + b, 0)} likes, ` +
      `${likes.filter((x) => x === 0).length} con 0 likes`);
  }

  console.log("\n=== Media de likes por tipo de contenido ===");
  const tipos = [...new Set(ok.map((r) => `${r.platform}:${r.type}`))].sort();
  console.log("lang | " + tipos.map((t) => t.padEnd(13)).join("| "));
  for (const lang of langs) {
    const celdas = tipos.map((t) => {
      const [p, ti] = t.split(":");
      const s = ok.filter((r) => r.lang === lang && r.platform === p && r.type === ti);
      return (s.length ? `${f2(med(s.map((r) => num(r.likes))))} (n=${s.length})` : "-").padEnd(13);
    });
    if (celdas.some((c) => c.trim() !== "-")) console.log(lang.padEnd(4) + " | " + celdas.join("| "));
  }

  const errores = filas.filter((r) => r.error);
  if (errores.length) {
    console.log(`\n=== ${errores.length} publicaciones no accesibles (normalmente borradas) ===`);
    const porIdioma = {};
    for (const e of errores) { const k = `${e.platform}:${e.lang}`; porIdioma[k] = (porIdioma[k] || 0) + 1; }
    for (const [k, v] of Object.entries(porIdioma).sort()) console.log(`  ${k.padEnd(8)} ${v}`);
  }

  if (JSON_OUT) {
    fs.writeFileSync(JSON_OUT, JSON.stringify({ generado: new Date().toISOString(), dias: DIAS, filas }, null, 1));
    console.log(`\nDatos completos en ${JSON_OUT}`);
  }
})();
