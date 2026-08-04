#!/usr/bin/env node
// Fusiona el estado de NUESTRA ejecución sobre el estado MÁS RECIENTE de origin.
//
// Por qué existe: dos publicaciones (FB :00 e IG :01) guardan state/ casi a la vez.
// El "git pull --rebase" del perdedor chocaba SIEMPRE en history.jsonl (los dos
// añaden líneas al final -> conflicto), los 5 reintentos re-ejecutaban el pull
// sobre un rebase roto y el estado se perdía -> rotación congelada -> DUPLICADOS
// (auditoría 04-08-2026: fb:articles 4 días sin guardar, mismo artículo 4 veces;
// ig tarde perdido día sí día no -> mismo ejercicio tarde+mañana).
//
// Con esto el guardado es POR FUSIÓN, imposible de conflictuar:
//   cp -r state /tmp/state_ours          (resultados de esta ejecución)
//   git reset --hard origin/main         (estado más reciente del repo)
//   node tools/merge_state.js /tmp/state_ours state
//   commit + push (reintentando: fetch+reset+merge de nuevo; idempotente)
//
// Uso: node tools/merge_state.js <dir_nuestro> <dir_base>
const fs = require("fs");
const path = require("path");

const [ours, base] = process.argv.slice(2);
if (!ours || !base) { console.error("uso: merge_state.js <dir_nuestro> <dir_base>"); process.exit(1); }

const readJSON = p => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch (e) { return null; } };
const readText = p => { try { return fs.readFileSync(p, "utf8"); } catch (e) { return null; } };

// posted_log.json — por clave: base + nuestros items que falten (al final = más recientes)
{
  const A = readJSON(path.join(ours, "posted_log.json"));
  const B = readJSON(path.join(base, "posted_log.json")) || {};
  if (A) {
    for (const k of Object.keys(A)) {
      const b = B[k] || [];
      for (const it of A[k]) if (!b.includes(it)) b.push(it);
      B[k] = b.slice(-500);
    }
    fs.writeFileSync(path.join(base, "posted_log.json"), JSON.stringify(B, null, 2) + "\n");
    console.log("[merge] posted_log.json fusionado");
  }
}

// published.json — unión de marcas de franja hecha (conserva las últimas ~40)
{
  const A = readJSON(path.join(ours, "published.json"));
  const B = readJSON(path.join(base, "published.json")) || {};
  if (A) {
    const M = { ...B, ...A };
    const keys = Object.keys(M).sort();
    for (const k of keys.slice(0, Math.max(0, keys.length - 40))) delete M[k];
    fs.writeFileSync(path.join(base, "published.json"), JSON.stringify(M, null, 2) + "\n");
    console.log("[merge] published.json fusionado");
  }
}

// history.jsonl — base + nuestras líneas que no estén ya (añadidas al final)
{
  const A = readText(path.join(ours, "history.jsonl"));
  if (A !== null) {
    const btxt = readText(path.join(base, "history.jsonl")) || "";
    const have = new Set(btxt.split("\n").filter(Boolean));
    const add = A.split("\n").filter(l => l.trim() && !have.has(l));
    if (add.length) fs.appendFileSync(path.join(base, "history.jsonl"), add.join("\n") + "\n");
    console.log(`[merge] history.jsonl: +${add.length} líneas`);
  }
}

// resto de archivos json de state/ (approvals, propagate_request...): gana el de base
// (no los toca esta ejecución); si solo existe en el nuestro, se copia.
for (const f of fs.readdirSync(ours)) {
  const dst = path.join(base, f);
  if (!fs.existsSync(dst)) fs.copyFileSync(path.join(ours, f), dst);
}
console.log("[merge] listo");
