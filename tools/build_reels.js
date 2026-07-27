// Genera config/reels.json (datos para el pipeline) + content/reels/REELS_LIST.md (lista legible)
// a partir de los 31 reels franceses. Traduce titulo + CTA + hashtags a los 6 idiomas (NO fr).
// Caption de reel = CORTO (el video muestra el ejercicio): gancho + CTA (50 ejercicios + guia jovenes) + hashtags.
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const LANGS = ['es', 'en', 'de', 'it', 'pt', 'nl'];

// ── Reels (orden original). theme = clave; plural = "Idées exercices"; dup marca repetidos ──
const REELS = [
  { n: 1,  id: '1951129368927387', theme: 'echauffement', plural: true },
  { n: 2,  id: '1163415026862701', theme: 'agilite' },
  { n: 3,  id: '4352454308336733', theme: 'jeu-reduit-duels' },
  { n: 4,  id: '2013595585917541', theme: 'echauffement' },
  { n: 5,  id: '1751582305999402', theme: 'echauffement' },
  { n: 6,  id: '2154251835355676', theme: 'vitesse' },
  { n: 7,  id: '808016639060483',  theme: 'echauffement' },
  { n: 8,  id: '5495512367341414', theme: 'vitesse-reaction-gainage' },
  { n: 9,  id: '1305650665083512', theme: 'echauffement' },
  { n: 10, id: '1716199756236138', theme: 'echauffement' },
  { n: 11, id: '2998496860338769', theme: 'agilite' },
  { n: 12, id: '26479037135113424', theme: 'echauffement' },
  { n: 13, id: '1410319904111204', theme: 'vitesse-reaction' },
  { n: 14, id: '1625589885398990', theme: 'coordination' },
  { n: 15, id: '2334653287018363', theme: 'vitesse' },
  { n: 16, id: '1662346061566915', theme: 'vitesse-agilite' },
  { n: 17, id: '1866420667358692', theme: 'vitesse-agilite' },
  { n: 18, id: '1586270882661847', theme: 'echauffement' },
  { n: 19, id: '1626771625427924', theme: 'echauffement' },
  { n: 20, id: '1219268500339449', theme: 'vitesse-agilite' },
  { n: 21, id: '906922768867523',  theme: 'echauffement' },
  { n: 22, id: '5495512367341414', theme: 'vitesse-reaction-gainage', dup: 8 },
  { n: 23, id: '26101317516170155', theme: 'echauffement' },
  { n: 24, id: '1223253979765464', theme: 'echauffement' },
  { n: 25, id: '982821941575485',  theme: 'vitesse' },
  { n: 26, id: '3727693974191112', theme: 'echauffement' },
  { n: 27, id: '901247298925250',  theme: 'vitesse-agilite' },
  { n: 28, id: '2319098585191579', theme: 'agilite-vitesse-reaction' },
  { n: 29, id: '24973896835545702', theme: 'vitesse-reaction', plural: true },
  { n: 30, id: '2118081678710096', theme: 'echauffement' },
  { n: 31, id: '418021344197607',  theme: 'echauffement-agilite-vivacite', plural: true },
];

// ── Traducciones de temas (nativas por idioma) ──
const THEME = {
  'echauffement':                 { es: 'calentamiento', en: 'warm-up', de: 'Aufwärmen', it: 'riscaldamento', pt: 'aquecimento', nl: 'opwarming' },
  'agilite':                      { es: 'agilidad', en: 'agility', de: 'Agilität', it: 'agilità', pt: 'agilidade', nl: 'wendbaarheid' },
  'vitesse':                      { es: 'velocidad', en: 'speed', de: 'Schnelligkeit', it: 'velocità', pt: 'velocidade', nl: 'snelheid' },
  'vitesse-reaction':             { es: 'velocidad de reacción', en: 'reaction speed', de: 'Reaktionsschnelligkeit', it: 'velocità di reazione', pt: 'velocidade de reação', nl: 'reactiesnelheid' },
  'vitesse-reaction-gainage':     { es: 'velocidad de reacción (y core)', en: 'reaction speed (and core)', de: 'Reaktionsschnelligkeit (und Rumpfstabilität)', it: 'velocità di reazione (e core)', pt: 'velocidade de reação (e core)', nl: 'reactiesnelheid (en corestabiliteit)' },
  'coordination':                 { es: 'coordinación', en: 'coordination', de: 'Koordination', it: 'coordinazione', pt: 'coordenação', nl: 'coördinatie' },
  'vitesse-agilite':              { es: 'velocidad y agilidad', en: 'speed & agility', de: 'Schnelligkeit & Agilität', it: 'velocità e agilità', pt: 'velocidade e agilidade', nl: 'snelheid & wendbaarheid' },
  'agilite-vitesse-reaction':     { es: 'agilidad y velocidad de reacción', en: 'agility & reaction speed', de: 'Agilität & Reaktionsschnelligkeit', it: 'agilità e velocità di reazione', pt: 'agilidade e velocidade de reação', nl: 'wendbaarheid & reactiesnelheid' },
  'jeu-reduit-duels':             { es: 'juego reducido — duelos', en: 'small-sided game — duels', de: 'Kleinfeldspiel — Duelle', it: 'partita a tema — duelli', pt: 'jogo reduzido — duelos', nl: 'partijspel — duels' },
  'echauffement-agilite-vivacite':{ es: 'calentamiento + agilidad y viveza', en: 'warm-up then agility & quickness', de: 'Aufwärmen, dann Agilität & Spritzigkeit', it: 'riscaldamento poi agilità e vivacità', pt: 'aquecimento + agilidade e vivacidade', nl: 'opwarming daarna wendbaarheid & felheid' },
};

// ── Prefijo "Idea de ejercicio" (sing) / "Ideas de ejercicios" (plural) ──
const PREFIX = {
  es: ['Idea de ejercicio', 'Ideas de ejercicios'],
  en: ['Exercise idea', 'Exercise ideas'],
  de: ['Übungsidee', 'Übungsideen'],
  it: ['Idea di esercizio', 'Idee di esercizi'],
  pt: ['Ideia de exercício', 'Ideias de exercícios'],
  nl: ['Oefenidee', 'Oefenideeën'],
};

// ── CTA (50 ejercicios + guia jovenes). Link home por idioma. IG: "enlace en la bio"; FB: url clicable ──
const CTA = {
  es: '🎁 50 ejercicios físicos gratis + guía de jóvenes futbolistas: www.ppf11.com/es o enlace en la bio.',
  en: '🎁 50 free physical exercises + young players guide: www.ppf11.com/en or link in bio.',
  de: '🎁 50 gratis Athletikübungen + Leitfaden für junge Fußballer: www.ppf11.com/de oder Link in der Bio.',
  it: '🎁 50 esercizi fisici gratis + guida per giovani calciatori: www.ppf11.com/it o link in bio.',
  pt: '🎁 50 exercícios físicos grátis + guia de jovens jogadores: www.ppf11.com/pt ou link na bio.',
  nl: '🎁 50 gratis fysieke oefeningen + gids voor jonge voetballers: www.ppf11.com/nl of link in bio.',
};

// ── Hashtags fijos por idioma (localizados del set frances) ──
const HASH = {
  es: '#preparaciónfísica #fútbol #entrenamiento #calentamiento #resistencia #velocidad',
  en: '#physicaltraining #football #soccer #warmup #endurance #speed',
  de: '#athletiktraining #fußball #training #aufwärmen #ausdauer #schnelligkeit',
  it: '#preparazionefisica #calcio #allenamento #riscaldamento #resistenza #velocità',
  pt: '#preparaçãofísica #futebol #treino #aquecimento #resistência #velocidade',
  nl: '#fysieketraining #voetbal #training #opwarming #uithoudingsvermogen #snelheid',
};

const title = (lang, r) => `⚽ ${PREFIX[lang][r.plural ? 1 : 0]}: ${THEME[r.theme][lang]} 🎁⬇️`;
const caption = (lang, r) => `${title(lang, r)}\n\n${CTA[lang]}\n\n${HASH[lang]}`;

// ── Salida JSON (para el pipeline) ──
const out = REELS.map(r => {
  const caps = {}, titles = {};
  for (const l of LANGS) { caps[l] = caption(l, r); titles[l] = title(l, r); }
  return {
    n: r.n,
    fb_url: `https://www.facebook.com/reel/${r.id}`,
    reel_id: r.id,
    theme_fr: r.theme,
    duplicate_of: r.dup || null,
    titles,
    captions: caps,
  };
});
fs.mkdirSync(path.join(ROOT, 'content', 'reels'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'config', 'reels.json'),
  JSON.stringify({
    _comment: 'Reels FR de PPF11 a re-publicar en IG+FB de los 6 idiomas (es/en/de/it/pt/nl). NO francés. Caption corto (el video muestra el ejercicio). Link CTA = home por idioma (revisar). CTA = 50 ejercicios + guía jóvenes.',
    supabase: { bucket: 'videos', folder: 'reels' },
    langs: LANGS,
    count: out.length,
    unique: out.filter(r => !r.duplicate_of).length,
    reels: out,
  }, null, 2) + '\n', 'utf8');

// ── Salida Markdown legible ──
let md = `# Reels PPF11 — lista traducida (6 idiomas)\n\n`;
md += `Reels franceses a re-publicar en **Instagram + Facebook** de los 6 idiomas (es/en/de/it/pt/nl). **Francés no se toca.**\n`;
md += `Caption corto (el vídeo muestra el ejercicio) = gancho + CTA (50 ejercicios + guía jóvenes) + hashtags.\n`;
md += `Total: ${out.length} reels (${out.filter(r=>r.duplicate_of).length} duplicado marcado). Link del CTA = home por idioma (dime si lo quieres genérico www.ppf11.com).\n\n---\n\n`;
const LNAME = { es: '🇪🇸 Español', en: '🇬🇧 English', de: '🇩🇪 Deutsch', it: '🇮🇹 Italiano', pt: '🇵🇹 Português', nl: '🇳🇱 Nederlands' };
for (const r of out) {
  md += `## Reel ${r.n}${r.duplicate_of ? ` — ⚠️ DUPLICADO del #${r.duplicate_of}` : ''}\n`;
  md += `**URL:** ${r.fb_url}\n\n`;
  for (const l of LANGS) {
    md += `**${LNAME[l]}**\n\n\`\`\`\n${r.captions[l]}\n\`\`\`\n\n`;
  }
  md += `---\n\n`;
}
fs.writeFileSync(path.join(ROOT, 'content', 'reels', 'REELS_LIST.md'), md, 'utf8');

console.log(`OK. ${out.length} reels x ${LANGS.length} idiomas.`);
console.log(`  config/reels.json  y  content/reels/REELS_LIST.md`);
console.log('\n===== MUESTRA (reel 3, es) =====\n' + out[2].captions.es);
console.log('\n===== MUESTRA (reel 14, en) =====\n' + out[13].captions.en);
