# EXTRACTION_NOTES — exercises.csv / articles.csv

Generado a partir de dos proyectos web locales (solo lectura). Fecha: 2026-07-22.

- Fuente 1: `ppf11` (`C:\Users\PC\Documents\ppf-proyectos-github\ppf11`) — idiomas **de, en, es, it, nl, pt**. Dominio de producción: `https://www.ppf11.com`
- Fuente 2: `ppf-fr` (`C:\Users\PC\Documents\ppf-proyectos-github\ppf-fr`) — idioma **fr**. Dominio: `https://www.preparationphysiquefootball.com`

Codificación de ambos CSV: **UTF-8 con BOM**. Todos los campos van entre comillas dobles; las comillas internas se escapan duplicándolas. Cabecera exacta: `language,title,summary,url,image_url,hashtags`.

---

## 1. Recuento final

### exercises.csv — 700 filas
| Idioma | Filas |
|--------|-------|
| es | 100 |
| en | 100 |
| de | 100 |
| it | 100 |
| nl | 100 |
| pt | 100 |
| fr | 100 |
| **Total** | **700** |

ppf11 = 100 ejercicios × 6 idiomas = 600. ppf-fr = 100 ejercicios × 1 idioma = 100.
Ningún ejercicio saltado: los 6 idiomas de ppf11 tienen los 100 títulos completos.

### articles.csv — 535 filas
| Idioma | Filas |
|--------|-------|
| es | 75 |
| en | 75 |
| de | 75 |
| it | 75 |
| nl | 75 |
| pt | 75 |
| fr | 85 |
| **Total** | **535** |

ppf11 = 75 artículos × 6 idiomas = 450. ppf-fr = 85 artículos (catálogo del blog).

---

## 2. El caso de los artículos ES (RESUELTO)

**ES SÍ tiene artículos (75).** No están en una carpeta `es/`; ES es el **idioma base** del blog:

- Base (ES, campos completos): `src/data/blog/articles/*.json` → 75 ficheros JSON con `slug, category, title, excerpt, readingMinutes, date, heroImage, blocks`.
- Traducciones (de/en/it/nl/pt): `src/data/blog/articles/<lang>/<slug>.json`, que contienen **solo** los campos traducibles `{ title, excerpt, blocks }`. Los campos neutros (`slug, category, heroImage`) se heredan de la base ES (ver `src/data/blog/index.ts`).
- El nombre de fichero es el **slug canónico ES** e **idéntico en todas las carpetas** de idioma (75 en cada una). Los 5 idiomas no-ES tienen los 75 ficheros de traducción presentes; no hubo que caer al fallback ES en ninguno.

Para cada fila de artículo: `title`/`summary` salen del JSON del idioma (o de la base ES en `es`); `image_url`/hashtags salen de la base ES.

---

## 3. Patrón de URL por idioma (con ejemplos reales)

Todos los idiomas de ppf11 —**incluido `es`**— se sirven bajo prefijo `/{lang}/`. La raíz `/` es el selector de idioma (x-default). Confirmado en `src/components/SeoManager.tsx` (`canonicalRelative` → `/${lang}${slug}`) y `src/routing/lang-url.ts`.

### Ejercicios
- **ppf11** — No existe página de detalle por ejercicio en el routing actual (MVP: `URL_MAP`/`PAGE_MAP` solo tienen la vista `free-exercises`). Los ejercicios se abren en modal dentro de la página-biblioteca. Por tanto **todos los ejercicios de un idioma comparten la URL de la página de ejercicios**:
  - es: `https://www.ppf11.com/es/entrenamientos/ejercicios-gratis`
  - en: `https://www.ppf11.com/en/training/free-exercises`
  - it: `https://www.ppf11.com/it/allenamenti/esercizi-gratuiti`
  - pt: `https://www.ppf11.com/pt/treinos/exercicios-gratis`
  - de: `https://www.ppf11.com/de/trainings/kostenlose-uebungen`
  - nl: `https://www.ppf11.com/nl/trainingen/gratis-oefeningen`
  - (slugs en `src/lib/free-exercises-slug.ts`)
- **ppf-fr** — SÍ hay página de detalle SEO por ejercicio (`src/router/urlMap.ts`, `FREE_EXERCISE_VIEW_PREFIX`). Patrón:
  - `https://www.preparationphysiquefootball.com/entrainements/exercices-gratuits/<slug>`
  - Ejemplo: `.../entrainements/exercices-gratuits/transition-defensive-travailler-le-reflexe`
  - `slug` = campo `slug` explícito (24 de 100) o `slugify(title)` con resolución de colisiones (sufijo `-<id>`), replicando exactamente `src/data/freeExercises.ts`.

### Artículos
- **ppf11** — índice en `/{lang}/blog`, artículos en `/{lang}/blog/<slug-traducido>`. El slug se traduce por idioma vía `src/data/blog/slug-i18n.ts`; `es` usa el slug canónico (nombre de fichero). Ejemplos del mismo artículo:
  - es: `https://www.ppf11.com/es/blog/10-cualidades-entrenador-futbol`
  - en: `https://www.ppf11.com/en/blog/10-qualities-a-coach-should-have`
  - de: `https://www.ppf11.com/de/blog/10-qualitaten-die-ein-trainer-haben-sollte`
- **ppf-fr** — cada artículo tiene su ruta (a menudo heredada/legacy) en `src/router/urlMap.ts`. Rutas heterogéneas: `/blog/<slug>`, `/2018/<slug>`, `/201707/<slug>`, `/2025/...`, etc. Ejemplos:
  - `https://www.preparationphysiquefootball.com/2026/pre-saison-avec-ou-sans-ballon`
  - `https://www.preparationphysiquefootball.com/blog/routine-recuperation-footballeur-blessures`
  - Los 85 artículos del catálogo (`BlogPage.tsx`) tienen entrada en `URL_MAP` (0 sin mapear).

---

## 4. Formato de las imágenes e idoneidad para Instagram (JPEG)

Instagram solo acepta **JPEG**. Resumen por dataset:

### Ejercicios — ⚠️ NO compatibles con IG (ACCIÓN PENDIENTE)
- `image_url` se construye con `dominio + cardImage`, tal como está en los datos: 686 rutas `.png` + 14 `.jpg` (los `.jpg` corresponden a `intermittents-34` e `intermittents-59` en ppf11 ×6 y sus equivalentes FR ×2).
- **Pero en la carpeta `public/images/free-exercises/` de AMBOS proyectos solo existen ficheros `.webp`.** El sitio sirve la versión `.webp` en tiempo de ejecución vía `<picture>` + `toWebp()` (sustituye `.png/.jpg`→`.webp`). Es decir:
  1. Las URL `.png`/`.jpg` de `image_url` puede que ni siquiera resuelvan (el binario real es `.webp`).
  2. **No existe ninguna versión JPEG real** de estas imágenes.
- **ACCIÓN PENDIENTE para IG:** generar/derivar versiones **JPEG** de las imágenes de ejercicio (convertir desde el `.webp`/fuente) y sustituir la extensión en `image_url`, o convertir on-the-fly en el momento de publicar. Sin esto, la publicación de ejercicios en Instagram fallará.

### Artículos — mayormente compatibles
- ppf11 (`heroImage`) es una **URL absoluta JPG** ya presente en los datos, servida desde el dominio FR: `https://www.preparationphysiquefootball.com/images/blog/<...>.jpg` (los 450 artículos ppf11 usan `.jpg`). → **JPEG, compatible con IG** (asumiendo que el fichero existe en el dominio FR). Nota: el `heroImage` en los datos de ppf11 ya apunta al dominio FR; se ha respetado literalmente.
- ppf-fr (85 artículos): distribución de extensiones en `image_url` del CSV completo → **jpg 506, png 22, webp 3, sin-extensión 4** (estas últimas son URLs de Unsplash con querystring, normalmente `fm=jpg`). Hosts: `preparationphysiquefootball.com` 525, `da32ev14kd4yl.cloudfront.net` 5, `images.unsplash.com` 4, `img.mailinblue.com` 1.
  - Los `.webp`/`.png` de artículos FR (p. ej. `fartlek-football-amateur.webp`, `circuit-training-football.png`) **necesitan conversión a JPEG** para IG.
  - 5 artículos FR usan imágenes de host externo (Unsplash/Cloudfront/Mailinblue) — probablemente placeholders de stock; revisar antes de publicar:
    - "25 idées de jeux réduits..." (mailinblue .png)
    - "C'est un test bien adapté au football" (unsplash)
    - "Le travail de vitesse en descente" (unsplash)
    - "Préparation physique estivale en football..." (unsplash)
    - "Circuit Training pour Footballeurs" (unsplash)

---

## 5. Hashtags

3 hashtags base por idioma + 1 derivado del tema (ejercicios) o de la categoría (artículos) → normalmente 4 por fila.

- es `#fútbol #entrenamiento #preparaciónfísica`
- en `#football #soccer #training`
- fr `#football #préparationphysique #entraînement`
- de `#fußball #training #athletik`
- it `#calcio #allenamento #preparazione`
- nl `#voetbal #training #conditie`
- pt `#futebol #treino #preparaçãofísica`

El tag temático se mapea desde `topic` del ejercicio (velocidad, resistencia, fuerza, intermitente, coordinación, transiciones, portero, futsal, etc.) o desde `category` del artículo (velocidad, resistencia, fuerza, prevención, mental, nutrición, gestión, jóvenes, futsal, portero, planificación, material, coordinación).

---

## 6. Supuestos y decisiones

- **Prefijo `/{lang}/` para todos los idiomas de ppf11, incluido `es`** (la raíz `/` es el selector). Fuente: `SeoManager.canonicalRelative`.
- **Ejercicios ppf11 sin página de detalle**: se usa la URL de la página-biblioteca del idioma para las 100 filas de cada idioma. Si en el futuro se añaden páginas de detalle por ejercicio, habrá que regenerar las URLs.
- **summary**: para ejercicios se usó `objectif` (fallback: inicio de `description`); para artículos, `excerpt`. Se eliminó markdown (`**`, `→`, `#`, viñetas), se colapsaron saltos de línea a espacios y se limitó a ~200 caracteres (corte por palabra + `…` si excedía). No hay resúmenes vacíos.
- **image_url de ejercicios**: se conservó la ruta `.png`/`.jpg` que aparece en los datos (según instrucción), pese a que el binario servido es `.webp`. Ver sección 4.
- **heroImage de artículos ppf11**: es absoluta en origen (dominio FR); se usó tal cual, sin reescribir a `ppf11.com`.
- **Artículos FR**: fuente única = el array `articles` de `src/components/BlogPage.tsx` (catálogo del índice del blog: 85 entradas con id/título/categoría/imagen/excerpt), en vez de parsear los ~90 componentes `BlogArticle*.tsx` individuales (mucho más costoso y frágil). Cada `id` se resolvió a su URL real vía `src/router/urlMap.ts`. Cobertura: 85/85 con URL. Los componentes `BlogArticle*.tsx` no aportan metadatos de tarjeta (título/excerpt/hero) de forma más fiable que este catálogo central.
- No se hicieron peticiones de red. Todo es lectura local + escritura de los 3 ficheros de `content/`.

---

## 7. Validación

Ambos CSV se parsearon con `Import-Csv` de PowerShell: 700 filas (exercises) y 535 filas (articles), 6 columnas, sin campos `summary` ni `image_url` vacíos. Recuentos por idioma correctos (sección 1).
