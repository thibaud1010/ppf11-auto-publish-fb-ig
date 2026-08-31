// Ensambla el caption final = CUERPO (content/captions/*.json) + CTA (config/cta.json con enlaces) + HASHTAGS.
// Rellena caption_ig y caption_fb en los CSV DE TRABAJO (content/exercises.csv, content/articles.csv).
// Parser RFC4180 (soporta campos multilínea entrecomillados) -> re-ejecutable sin corromper.
//   node tools/assemble_captions.js
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const rd = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8').replace(/^﻿/, ''));

const LINKS = rd('config/links.json').free_exercises;
const CTA = rd('config/cta.json');
const HASH = rd('config/hashtags.json');            // { idioma: hashtags base }
const THEMES = rd('config/hashtags_themes.json');   // { categoria: { idioma: trio } }

// categoria del ejercicio a partir del image_url: .../exercises/<marca>/<categoria>/...
// (marca = ppf11 para es/en/de/it/nl/pt, fr para frances). Devuelve '' si no casa.
const catOf = img => { const m = String(img||'').match(/exercises\/[^/]+\/([a-z-]+)\//); return m ? m[1] : ''; };
const themeTrio = (cat, lang) => (THEMES[cat] && THEMES[cat][lang]) || '';
// indice determinista 0..n-1 derivado del image_url (mismo calculo en propagate_captions.py):
// suma de codigos de caracter mod n. Estable e idempotente; reparte las 6 variantes de CTA.
const variantIdx = (img, n) => { if(!n) return 0; let s=0; const t=String(img); for(let i=0;i<t.length;i++) s+=t.charCodeAt(i); return s % n; };
// hashtags de EJERCICIO = base del idioma + trio tecnico de la categoria.
const exTags = (lang, cat) => `${(HASH[lang]||'').trim()} ${themeTrio(cat,lang).trim()}`.trim().replace(/\s+/g,' ');

// Parser CSV correcto: un salto de línea DENTRO de comillas NO separa filas.
function parseCSV(text){
  text = text.replace(/^﻿/, '');
  const rows=[]; let row=[]; let cur=''; let q=false;
  for(let i=0;i<text.length;i++){ const c=text[i];
    if(q){ if(c==='"'){ if(text[i+1]==='"'){cur+='"';i++;} else q=false; } else cur+=c; }
    else { if(c==='"') q=true;
      else if(c===','){ row.push(cur); cur=''; }
      else if(c==='\n'){ row.push(cur); rows.push(row); row=[]; cur=''; }
      else if(c==='\r'){ /* ignora */ }
      else cur+=c; } }
  if(cur.length || row.length){ row.push(cur); rows.push(row); }
  return rows;
}
const qf = s => '"' + String(s==null?'':s).replace(/"/g,'""') + '"';
const tags = (lang, topic) => `${(HASH[lang]||'').trim()} ${(topic||'').trim()}`.trim().replace(/\s+/g,' ');

function bodies(kind, lang){
  const p = path.join(ROOT,'content','captions',`${kind}_${lang}.json`);
  return fs.existsSync(p) ? rd(`content/captions/${kind}_${lang}.json`) : {};
}

function assemble(kind, csvName){
  const raw = fs.readFileSync(path.join(ROOT,'content',csvName),'utf8');
  const bom = raw.charCodeAt(0)===0xFEFF;
  const eol = raw.includes('\r\n') ? '\r\n' : '\n';
  const rows = parseCSV(raw);
  const header = rows[0];
  const idx = Object.fromEntries(header.map((h,i)=>[h,i]));
  const ensure = c => { if(!(c in idx)){ header.push(c); idx[c]=header.length-1; } };
  ensure('caption_ig'); ensure('caption_fb');

  const cache = {};
  let filled=0, missing=0;
  const out = [header.map(qf).join(',')];
  for(const r of rows.slice(1)){
    const f = r.slice(); while(f.length<header.length) f.push('');
    const lang=f[idx.language], img=f[idx.image_url], topic=f[idx.hashtags], url=f[idx.url];
    const b = (cache[lang+kind] ||= bodies(kind,lang))[img];
    if(b){
      const freeEx = LINKS[lang]||'';
      if(kind==='exercises'){
        const cat = catOf(img);
        const ht = exTags(lang, cat);                         // base + trio de la categoria
        const igArr = CTA.exercise.ig[lang];                  // array de 6 variantes
        const igCta = Array.isArray(igArr) ? (igArr[variantIdx(img, igArr.length)]||'') : (igArr||'');
        f[idx.caption_ig] = `${b}\n\n${igCta}\n\n${ht}`;
        f[idx.caption_fb] = `${b}\n\n${(CTA.exercise.fb[lang]||'').replace(/\{free_ex\}/g,freeEx).replace(/\{exercise_url\}/g,url)}\n\n${ht}`;
      } else {
        const ht = tags(lang, topic);                         // articulos: base + tag de tema del CSV (sin cambios)
        f[idx.caption_fb] = `${b}\n\n${(CTA.article.fb[lang]||'').replace(/\{article_url\}/g,url).replace(/\{free_ex\}/g,freeEx)}\n\n${ht}`;
        f[idx.caption_ig] = '';
      }
      filled++;
    } else missing++;
    out.push(f.map(qf).join(','));
  }
  let text = out.join(eol) + eol; if(bom) text = '﻿'+text;
  fs.writeFileSync(path.join(ROOT,'content',csvName), text, 'utf8');
  console.log(`${csvName}: filas=${rows.length-1} con_caption=${filled} sin_cuerpo=${missing}`);
}

assemble('exercises','exercises.csv');
assemble('articles','articles.csv');
console.log('Ensamblado completo.');
