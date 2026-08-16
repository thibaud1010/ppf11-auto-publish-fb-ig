// Genera config/reels.json (datos para el pipeline) + content/reels/REELS_LIST.md (lista legible)
// a partir de los 31 reels franceses, en los 6 idiomas (NO fr).
//
// Caption = gancho con beneficio + linea de valor (que trabaja el ejercicio) + CTA de CONVERSION + hashtags.
// DOS VERSIONES por reel e idioma:
//   A -> regalo "50 ejercicios" (PDF, esquemas 3D)
//   B -> regalo "guia de los jovenes futbolistas"
// publish_reels.py alterna A/B segun las veces que ese reel ya se publico, asi que
// al republicarse (ciclo 2+) el caption NO es identico (mejor para Meta y para quien ya lo vio).
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const LANGS = ['es', 'en', 'de', 'it', 'pt', 'nl'];

// ── Reels (orden original). theme = clave; dup marca repetidos ──
const REELS = [
  { n: 1,  id: '1951129368927387', theme: 'echauffement' },
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
  { n: 29, id: '24973896835545702', theme: 'vitesse-reaction' },
  { n: 30, id: '2118081678710096', theme: 'echauffement' },
  { n: 31, id: '418021344197607',  theme: 'echauffement-agilite-vivacite' },
];

// ── COPY por tema: h = gancho (lo primero que se ve), v = linea de valor ──
// Redactado nativo en cada idioma (no traduccion literal), con termino futbolistico.
const COPY = {
  'echauffement': {
    es: { h: 'Calentamiento: llegar al primer duelo a tope',
          v: 'Movilidad, activación y subida progresiva de ritmo. Un buen calentamiento no cansa: prepara.' },
    en: { h: 'Warm-up: ready for the first duel',
          v: 'Mobility, activation and a progressive rise in intensity. A good warm-up doesn’t tire you out — it gets you ready.' },
    de: { h: 'Aufwärmen: bereit für den ersten Zweikampf',
          v: 'Mobilität, Aktivierung und progressiver Intensitätsaufbau. Gutes Aufwärmen ermüdet nicht — es macht bereit.' },
    it: { h: 'Riscaldamento: pronti al primo duello',
          v: 'Mobilità, attivazione e aumento progressivo del ritmo. Un buon riscaldamento non stanca: prepara.' },
    pt: { h: 'Aquecimento: chegar no primeiro duelo no máximo',
          v: 'Mobilidade, ativação e subida progressiva de ritmo. Um bom aquecimento não cansa: prepara.' },
    nl: { h: 'Opwarming: klaar voor het eerste duel',
          v: 'Mobiliteit, activatie en een geleidelijke opbouw van intensiteit. Een goede opwarming vermoeit niet — die maakt scherp.' },
  },
  'agilite': {
    es: { h: 'Agilidad: cambiar de dirección sin perder velocidad',
          v: 'Apoyos, frenada y reaceleración: la base para ganar el primer metro.' },
    en: { h: 'Agility: change direction without losing speed',
          v: 'Footwork, braking and re-acceleration — the base for winning the first metre.' },
    de: { h: 'Agilität: Richtungswechsel ohne Tempoverlust',
          v: 'Schrittarbeit, Abbremsen und Wiederbeschleunigung — die Basis, um den ersten Meter zu gewinnen.' },
    it: { h: 'Agilità: cambiare direzione senza perdere velocità',
          v: 'Appoggi, frenata e riaccelerazione: la base per vincere il primo metro.' },
    pt: { h: 'Agilidade: mudar de direção sem perder velocidade',
          v: 'Apoios, frenagem e reaceleração: a base para ganhar o primeiro metro.' },
    nl: { h: 'Wendbaarheid: van richting veranderen zonder snelheid te verliezen',
          v: 'Voetenwerk, afremmen en opnieuw versnellen — de basis om de eerste meter te winnen.' },
  },
  'jeu-reduit-duels': {
    es: { h: 'Juego reducido: duelos que se parecen al partido',
          v: 'Espacio corto y oposición real: intensidad, decisión y competición en cada acción.' },
    en: { h: 'Small-sided game: duels that look like the match',
          v: 'Tight space and real opposition — intensity, decision-making and competition in every action.' },
    de: { h: 'Kleinfeldspiel: Duelle wie im Spiel',
          v: 'Enger Raum und echter Gegner — Intensität, Entscheidungen und Wettkampf in jeder Aktion.' },
    it: { h: 'Partita a tema: duelli che somigliano alla gara',
          v: 'Spazio stretto e opposizione reale: intensità, scelte e competizione in ogni azione.' },
    pt: { h: 'Jogo reduzido: duelos parecidos com o jogo',
          v: 'Espaço curto e oposição real: intensidade, decisão e competição em cada ação.' },
    nl: { h: 'Partijspel: duels zoals in de wedstrijd',
          v: 'Kleine ruimte en echte tegenstand — intensiteit, keuzes en competitie in elke actie.' },
  },
  'vitesse': {
    es: { h: 'Velocidad: ganar el metro que decide la jugada',
          v: 'Salidas, zancada y máxima intensidad en distancias cortas, como en el partido.' },
    en: { h: 'Speed: win the metre that decides the play',
          v: 'Starts, stride and maximum intensity over short distances — just like in the match.' },
    de: { h: 'Schnelligkeit: den entscheidenden Meter gewinnen',
          v: 'Antritte, Schrittlänge und maximale Intensität auf kurzen Distanzen — wie im Spiel.' },
    it: { h: 'Velocità: vincere il metro che decide l’azione',
          v: 'Partenze, falcata e massima intensità su distanze brevi, come in partita.' },
    pt: { h: 'Velocidade: ganhar o metro que decide o lance',
          v: 'Arrancadas, passada e máxima intensidade em distâncias curtas, como no jogo.' },
    nl: { h: 'Snelheid: de meter winnen die de actie beslist',
          v: 'Starts, pasfrequentie en maximale intensiteit over korte afstanden — net als in de wedstrijd.' },
  },
  'vitesse-reaction-gainage': {
    es: { h: 'Reacción y core: salir fuerte desde cualquier posición',
          v: 'Estímulo, arranque y estabilidad del tronco para no perder el equilibrio en el duelo.' },
    en: { h: 'Reaction & core: explode from any position',
          v: 'Cue, start and trunk stability — so you don’t lose your balance in the duel.' },
    de: { h: 'Reaktion & Rumpf: aus jeder Position explosiv starten',
          v: 'Reiz, Antritt und Rumpfstabilität — damit du im Zweikampf nicht aus dem Gleichgewicht gerätst.' },
    it: { h: 'Reazione e core: partire forte da qualsiasi posizione',
          v: 'Stimolo, scatto e stabilità del tronco per non perdere l’equilibrio nel duello.' },
    pt: { h: 'Reação e core: sair forte de qualquer posição',
          v: 'Estímulo, arrancada e estabilidade do tronco para não perder o equilíbrio no duelo.' },
    nl: { h: 'Reactie & core: explosief starten vanuit elke houding',
          v: 'Prikkel, start en rompstabiliteit — zodat je in het duel niet uit balans raakt.' },
  },
  'vitesse-reaction': {
    es: { h: 'Velocidad de reacción: el primer paso lo decide todo',
          v: 'Estímulo visual y arranque inmediato: entrena lo que pasa en la primera décima.' },
    en: { h: 'Reaction speed: the first step decides it',
          v: 'Visual cue, immediate start — train what happens in the first tenth of a second.' },
    de: { h: 'Reaktionsschnelligkeit: der erste Schritt entscheidet',
          v: 'Optischer Reiz, sofortiger Antritt — trainiere, was in der ersten Zehntelsekunde passiert.' },
    it: { h: 'Velocità di reazione: il primo passo decide tutto',
          v: 'Stimolo visivo e scatto immediato: allena ciò che accade nel primo decimo.' },
    pt: { h: 'Velocidade de reação: o primeiro passo decide tudo',
          v: 'Estímulo visual e arrancada imediata: treina o que acontece no primeiro décimo.' },
    nl: { h: 'Reactiesnelheid: de eerste stap beslist',
          v: 'Visuele prikkel, directe start — train wat er in de eerste tiende seconde gebeurt.' },
  },
  'coordination': {
    es: { h: 'Coordinación: pies rápidos, cuerpo bajo control',
          v: 'Frecuencia, ritmo y control del apoyo para moverte mejor con y sin balón.' },
    en: { h: 'Coordination: fast feet, body under control',
          v: 'Frequency, rhythm and foot control — to move better with and without the ball.' },
    de: { h: 'Koordination: schnelle Füße, Körper unter Kontrolle',
          v: 'Frequenz, Rhythmus und Fußkontrolle — um dich mit und ohne Ball besser zu bewegen.' },
    it: { h: 'Coordinazione: piedi rapidi, corpo sotto controllo',
          v: 'Frequenza, ritmo e controllo dell’appoggio per muoverti meglio con e senza palla.' },
    pt: { h: 'Coordenação: pés rápidos, corpo sob controle',
          v: 'Frequência, ritmo e controle do apoio para se mover melhor com e sem bola.' },
    nl: { h: 'Coördinatie: snelle voeten, lichaam onder controle',
          v: 'Frequentie, ritme en voetcontrole — om beter te bewegen met en zonder bal.' },
  },
  'vitesse-agilite': {
    es: { h: 'Velocidad y agilidad: acelerar, frenar y volver a salir',
          v: 'Cambios de dirección a máxima intensidad, como en una transición real.' },
    en: { h: 'Speed & agility: accelerate, brake, go again',
          v: 'Changes of direction at maximum intensity — like a real transition.' },
    de: { h: 'Schnelligkeit & Agilität: beschleunigen, abbremsen, wieder los',
          v: 'Richtungswechsel bei maximaler Intensität — wie in einer echten Umschaltsituation.' },
    it: { h: 'Velocità e agilità: accelerare, frenare e ripartire',
          v: 'Cambi di direzione a massima intensità, come in una transizione vera.' },
    pt: { h: 'Velocidade e agilidade: acelerar, frear e sair de novo',
          v: 'Mudanças de direção em máxima intensidade, como numa transição real.' },
    nl: { h: 'Snelheid & wendbaarheid: versnellen, afremmen, weer gaan',
          v: 'Richtingsveranderingen op maximale intensiteit — als in een echte omschakeling.' },
  },
  'agilite-vitesse-reaction': {
    es: { h: 'Agilidad y reacción: leer el estímulo y salir ya',
          v: 'Apoyos rápidos y respuesta inmediata: agilidad aplicada a la situación de juego.' },
    en: { h: 'Agility & reaction: read the cue and go',
          v: 'Quick footwork and immediate response — agility applied to a game situation.' },
    de: { h: 'Agilität & Reaktion: Reiz lesen und sofort los',
          v: 'Schnelle Schritte und sofortige Reaktion — Agilität in der Spielsituation.' },
    it: { h: 'Agilità e reazione: leggere lo stimolo e partire subito',
          v: 'Appoggi rapidi e risposta immediata: agilità applicata alla situazione di gioco.' },
    pt: { h: 'Agilidade e reação: ler o estímulo e sair já',
          v: 'Apoios rápidos e resposta imediata: agilidade aplicada à situação de jogo.' },
    nl: { h: 'Wendbaarheid & reactie: prikkel lezen en meteen gaan',
          v: 'Snelle voeten en directe respons — wendbaarheid in de spelsituatie.' },
  },
  'echauffement-agilite-vivacite': {
    es: { h: 'Calentamiento con agilidad: activar y despertar la viveza',
          v: 'Del movimiento suave a los apoyos rápidos, para entrar a la sesión enchufado.' },
    en: { h: 'Warm-up with agility: activate and switch on',
          v: 'From smooth movement to quick feet — so you start the session switched on.' },
    de: { h: 'Aufwärmen mit Agilität: aktivieren und wach werden',
          v: 'Von der ruhigen Bewegung zu schnellen Schritten — damit du hellwach in die Einheit startest.' },
    it: { h: 'Riscaldamento con agilità: attivare e svegliare la vivacità',
          v: 'Dal movimento morbido agli appoggi rapidi, per entrare in seduta sul pezzo.' },
    pt: { h: 'Aquecimento com agilidade: ativar e despertar a vivacidade',
          v: 'Do movimento suave aos apoios rápidos, para entrar no treino ligado.' },
    nl: { h: 'Opwarming met wendbaarheid: activeren en scherp worden',
          v: 'Van rustige beweging naar snelle voeten — zodat je scherp aan de sessie begint.' },
  },
};

// ── CTA A: regalo "50 ejercicios" (PDF + esquemas 3D + aplicable ya) ──
const CTA_A = {
  es: '🎁 Te regalo 50 EJERCICIOS en PDF\nEsquemas 3D, listos para imprimir y aplicar en tu próxima sesión.\n👉 Descarga gratis en ppf11.com/es — enlace en la bio',
  en: '🎁 I’m giving you 50 EXERCISES in PDF\n3D diagrams, ready to print and use in your next session.\n👉 Free download at ppf11.com/en — link in bio',
  de: '🎁 Ich schenke dir 50 ÜBUNGEN als PDF\n3D-Grafiken, direkt zum Ausdrucken und Einsetzen in der nächsten Einheit.\n👉 Gratis herunterladen auf ppf11.com/de — Link in der Bio',
  it: '🎁 Ti regalo 50 ESERCIZI in PDF\nSchemi 3D, pronti da stampare e usare nella prossima seduta.\n👉 Scarica gratis su ppf11.com/it — link in bio',
  pt: '🎁 Ganhe 50 EXERCÍCIOS em PDF\nEsquemas 3D, prontos para imprimir e aplicar no seu próximo treino.\n👉 Baixe grátis em ppf11.com/pt — link na bio',
  nl: '🎁 Ik geef je 50 OEFENINGEN in PDF\n3D-schema’s, klaar om te printen en direct te gebruiken in je volgende training.\n👉 Gratis downloaden op ppf11.com/nl — link in bio',
};

// ── CTA B: regalo "guia de los jovenes futbolistas" ──
const CTA_B = {
  es: '🎁 Te regalo la GUÍA DE LOS JÓVENES FUTBOLISTAS\n👉 Descarga inmediata y gratis en ppf11.com/es — enlace en la bio',
  en: '🎁 I’m giving you the YOUNG PLAYERS GUIDE\n👉 Instant free download at ppf11.com/en — link in bio',
  de: '🎁 Ich schenke dir den LEITFADEN FÜR JUNGE FUSSBALLER\n👉 Sofort und gratis herunterladen auf ppf11.com/de — Link in der Bio',
  it: '🎁 Ti regalo la GUIDA DEI GIOVANI CALCIATORI\n👉 Download immediato e gratuito su ppf11.com/it — link in bio',
  pt: '🎁 Ganhe o GUIA DOS JOVENS JOGADORES\n👉 Download imediato e grátis em ppf11.com/pt — link na bio',
  nl: '🎁 Ik geef je de GIDS VOOR JONGE VOETBALLERS\n👉 Direct en gratis downloaden op ppf11.com/nl — link in bio',
};

// ── Hashtags: base por idioma + 1 etiqueta del tema (relevante, no siempre las mismas) ──
const HASH_BASE = {
  es: '#preparaciónfísica #fútbol #entrenamiento',
  en: '#physicaltraining #football #soccer',
  de: '#athletiktraining #fußball #training',
  it: '#preparazionefisica #calcio #allenamento',
  pt: '#preparaçãofísica #futebol #treino',
  nl: '#fysieketraining #voetbal #training',
};
const HASH_THEME = {
  'echauffement':                 { es: '#calentamiento', en: '#warmup', de: '#aufwärmen', it: '#riscaldamento', pt: '#aquecimento', nl: '#opwarming' },
  'agilite':                      { es: '#agilidad', en: '#agility', de: '#agilität', it: '#agilità', pt: '#agilidade', nl: '#wendbaarheid' },
  'jeu-reduit-duels':             { es: '#juegoreducido', en: '#smallsidedgames', de: '#kleinfeldspiel', it: '#partiteatema', pt: '#jogoreduzido', nl: '#partijspel' },
  'vitesse':                      { es: '#velocidad', en: '#speed', de: '#schnelligkeit', it: '#velocità', pt: '#velocidade', nl: '#snelheid' },
  'vitesse-reaction-gainage':     { es: '#velocidad #core', en: '#speed #core', de: '#schnelligkeit #rumpfstabilität', it: '#velocità #core', pt: '#velocidade #core', nl: '#snelheid #core' },
  'vitesse-reaction':             { es: '#reacción #velocidad', en: '#reaction #speed', de: '#reaktion #schnelligkeit', it: '#reazione #velocità', pt: '#reação #velocidade', nl: '#reactie #snelheid' },
  'coordination':                 { es: '#coordinación', en: '#coordination', de: '#koordination', it: '#coordinazione', pt: '#coordenação', nl: '#coördinatie' },
  'vitesse-agilite':              { es: '#velocidad #agilidad', en: '#speed #agility', de: '#schnelligkeit #agilität', it: '#velocità #agilità', pt: '#velocidade #agilidade', nl: '#snelheid #wendbaarheid' },
  'agilite-vitesse-reaction':     { es: '#agilidad #reacción', en: '#agility #reaction', de: '#agilität #reaktion', it: '#agilità #reazione', pt: '#agilidade #reação', nl: '#wendbaarheid #reactie' },
  'echauffement-agilite-vivacite':{ es: '#calentamiento #agilidad', en: '#warmup #agility', de: '#aufwärmen #agilität', it: '#riscaldamento #agilità', pt: '#aquecimento #agilidade', nl: '#opwarming #wendbaarheid' },
};

const title = (lang, r) => `⚽ ${COPY[r.theme][lang].h}`;
const hashtags = (lang, r) => `${HASH_BASE[lang]} ${HASH_THEME[r.theme][lang]}`;
const caption = (lang, r, cta) =>
  `${title(lang, r)}\n\n${COPY[r.theme][lang].v}\n\n${cta[lang]}\n\n${hashtags(lang, r)}`;

// ── Salida JSON (para el pipeline) ──
const out = REELS.map(r => {
  const capsA = {}, capsB = {}, titles = {};
  for (const l of LANGS) {
    titles[l] = title(l, r);
    capsA[l] = caption(l, r, CTA_A);
    capsB[l] = caption(l, r, CTA_B);
  }
  return {
    n: r.n,
    fb_url: `https://www.facebook.com/reel/${r.id}`,
    reel_id: r.id,
    theme_fr: r.theme,
    duplicate_of: r.dup || null,
    titles,
    captions: capsA,    // version A (regalo: 50 ejercicios) — la que usa el ciclo 1
    captions_b: capsB,  // version B (regalo: guia jovenes) — al republicarse
  };
});
fs.mkdirSync(path.join(ROOT, 'content', 'reels'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'config', 'reels.json'),
  JSON.stringify({
    _comment: 'Reels FR de PPF11 a re-publicar en IG+FB de los 6 idiomas (es/en/de/it/pt/nl). NO frances. Caption = gancho + linea de valor + CTA de conversion + hashtags. DOS versiones: captions (A: regalo 50 ejercicios) y captions_b (B: regalo guia jovenes); publish_reels.py alterna segun las veces publicado, asi el repost no es identico.',
    supabase: { bucket: 'videos', folder: 'reels' },
    langs: LANGS,
    count: out.length,
    unique: out.filter(r => !r.duplicate_of).length,
    reels: out,
  }, null, 2) + '\n', 'utf8');

// ── Salida Markdown legible ──
const LNAME = { es: '🇪🇸 Español', en: '🇬🇧 English', de: '🇩🇪 Deutsch', it: '🇮🇹 Italiano', pt: '🇧🇷 Português', nl: '🇳🇱 Nederlands' };
let md = `# Reels PPF11 — lista traducida (6 idiomas)\n\n`;
md += `Reels franceses a re-publicar en **Instagram + Facebook** de los 6 idiomas (es/en/de/it/pt/nl). **Francés no se toca.**\n\n`;
md += `Cada reel tiene **dos versiones de caption** (gancho + línea de valor + CTA + hashtags):\n`;
md += `- **A** — regalo: 50 ejercicios en PDF (esquemas 3D). Es la que sale la primera vez.\n`;
md += `- **B** — regalo: guía de los jóvenes futbolistas. Sale cuando el reel se republica.\n\n`;
md += `Total: ${out.length} reels (${out.filter(r=>r.duplicate_of).length} duplicado marcado).\n\n---\n\n`;
for (const r of out) {
  md += `## Reel ${r.n} — ${r.theme_fr}${r.duplicate_of ? ` — ⚠️ DUPLICADO del #${r.duplicate_of}` : ''}\n`;
  md += `**URL:** ${r.fb_url}\n\n`;
  for (const l of LANGS) {
    md += `**${LNAME[l]} · versión A**\n\n\`\`\`\n${r.captions[l]}\n\`\`\`\n\n`;
    md += `**${LNAME[l]} · versión B**\n\n\`\`\`\n${r.captions_b[l]}\n\`\`\`\n\n`;
  }
  md += `---\n\n`;
}
fs.writeFileSync(path.join(ROOT, 'content', 'reels', 'REELS_LIST.md'), md, 'utf8');

console.log(`OK. ${out.length} reels x ${LANGS.length} idiomas x 2 versiones.`);
console.log(`  config/reels.json  y  content/reels/REELS_LIST.md`);
const maxLen = Math.max(...out.flatMap(r => LANGS.flatMap(l => [r.captions[l].length, r.captions_b[l].length])));
console.log(`  caption mas largo: ${maxLen} caracteres (limite IG 2200)`);
console.log('\n===== MUESTRA reel 1 (es) · versión A =====\n' + out[0].captions.es);
console.log('\n===== MUESTRA reel 1 (es) · versión B =====\n' + out[0].captions_b.es);
console.log('\n===== MUESTRA reel 3 (pt) · versión A =====\n' + out[2].captions.pt);
console.log('\n===== MUESTRA reel 14 (de) · versión B =====\n' + out[13].captions_b.de);
