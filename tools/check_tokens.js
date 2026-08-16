#!/usr/bin/env node
// Revisa los 11 tokens: validez, permisos y caducidad.
//
// Por que existe: la auditoria del 16-08-2026 descubrio que a los 7 tokens de
// Pagina les faltaba `pages_manage_engagement`, asi que el comentario con los
// enlaces fallaba SIEMPRE y nadie se entero en 13 dias. Con esto se ve en un
// comando que permisos tiene cada token y cuando caduca su acceso a datos.
//
// Uso:
//   node tools/check_tokens.js            (lee config/secrets.json o TOKENS_JSON)
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const V = process.env.GRAPH_VERSION || "v21.0";
const FB = `https://graph.facebook.com/${V}`;
const IGL = `https://graph.instagram.com/${V}`;

// Permisos que el sistema NECESITA en cada token de Pagina.
const REQUIRED = {
  pages_manage_posts: "publicar la foto",
  pages_manage_engagement: "publicar el comentario con los enlaces",
  instagram_content_publish: "publicar en Instagram (cuentas mode=page)",
  read_insights: "leer el alcance de la Pagina",
  instagram_manage_insights: "leer el alcance de Instagram (cuentas mode=page)",
};

function loadTokens() {
  const t = {};
  if (process.env.TOKENS_JSON) Object.assign(t, JSON.parse(process.env.TOKENS_JSON));
  const p = path.join(ROOT, "config/secrets.json");
  if (fs.existsSync(p)) Object.assign(t, JSON.parse(fs.readFileSync(p, "utf8")));
  return t;
}

async function api(url, params) {
  const u = new URL(url);
  for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  try {
    const r = await fetch(u, { signal: AbortSignal.timeout(30000) });
    const j = await r.json().catch(() => ({}));
    return r.ok ? j : { __error: j?.error?.message || `HTTP ${r.status}` };
  } catch (e) {
    return { __error: String(e.message || e) };
  }
}

const fecha = (ts) => (ts ? new Date(ts * 1000).toISOString().slice(0, 10) : "nunca");
const dias = (ts) => (ts ? Math.round((ts * 1000 - Date.now()) / 86400000) : null);

(async () => {
  const tokens = loadTokens();
  const accounts = JSON.parse(fs.readFileSync(path.join(ROOT, "config/accounts.json"), "utf8")).languages;
  const langs = Object.keys(accounts);
  let problemas = 0;

  console.log("\n=== TOKENS DE PAGINA (Facebook) ===");
  for (const lang of langs) {
    const name = `FB_TOKEN_${lang.toUpperCase()}`;
    const token = tokens[name];
    if (!token) { console.log(`${lang.padEnd(3)} FALTA ${name}`); problemas++; continue; }
    const r = await api(`${FB}/debug_token`, { input_token: token, access_token: token });
    if (r.__error) { console.log(`${lang.padEnd(3)} ERROR: ${r.__error}`); problemas++; continue; }
    const d = r.data || {};
    const scopes = d.scopes || [];
    const faltan = Object.keys(REQUIRED).filter((s) => !scopes.includes(s));
    const dAcc = dias(d.data_access_expires_at);
    console.log(
      `${lang.padEnd(3)} ${d.is_valid ? "valido" : "NO VALIDO"} | ` +
      `caduca: ${d.expires_at ? fecha(d.expires_at) : "nunca"} | ` +
      `acceso a datos: ${fecha(d.data_access_expires_at)}${dAcc !== null ? ` (${dAcc} dias)` : ""}`
    );
    if (!d.is_valid) problemas++;
    if (dAcc !== null && dAcc < 21) { console.log(`      AVISO: el acceso a datos caduca en ${dAcc} dias -> regenera los tokens`); problemas++; }
    if (faltan.length) {
      problemas++;
      console.log(`      FALTAN PERMISOS: ${faltan.join(", ")}`);
      for (const f of faltan) console.log(`         - ${f}: ${REQUIRED[f]}`);
    }
  }

  console.log("\n=== TOKENS DE INSTAGRAM LOGIN (cuentas mode=login) ===");
  for (const lang of langs) {
    if ((accounts[lang].instagram || {}).mode !== "login") continue;
    const name = `IG_TOKEN_${lang.toUpperCase()}`;
    const token = tokens[name];
    if (!token) { console.log(`${lang.padEnd(3)} FALTA ${name}`); problemas++; continue; }
    const r = await api(`${IGL}/me`, { fields: "username,account_type,followers_count,media_count", access_token: token });
    if (r.__error) { console.log(`${lang.padEnd(3)} NO VALIDO: ${r.__error}`); problemas++; continue; }
    console.log(`${lang.padEnd(3)} valido | @${r.username} | ${r.followers_count} seguidores | ${r.media_count} publicaciones`);
  }

  console.log(
    "\n" +
    (problemas
      ? `${problemas} cosa(s) que revisar. Para arreglar los permisos: anadirlos en la app de Meta y REGENERAR los tokens con tools/mint_fb_tokens.html.`
      : "Todo correcto.")
  );
  process.exit(problemas ? 1 : 0);
})();
