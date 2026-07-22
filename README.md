# Publicación automática en Facebook e Instagram

Sistema de publicación programada, **separado por plataforma**:

- **Facebook** (7 Páginas / 7 idiomas): 2 posts al día en 2 horarios distintos
  → uno de un **artículo del blog**, otro de un **ejercicio gratis**.
- **Instagram** (7 cuentas / 7 idiomas): 2 posts de **ejercicios** al día en 2 horarios distintos.

Cada publicación lleva **imagen + texto (plantilla) + enlace**. Usa las **APIs oficiales de Meta** (sin riesgo de bloqueo). Corre 24/7 en **GitHub Actions** (gratis, sin servidor).

---

## 1. Cómo funciona

```
Pipeline FACEBOOK                              Pipeline INSTAGRAM
  Horario A → publish_facebook.py --type article    Horario C → publish_instagram.py
  Horario B → publish_facebook.py --type exercise   Horario D → publish_instagram.py
     (recorre las 7 Páginas)                            (recorre las 7 cuentas)
```

- El **contenido** vive en `content/articles.csv` y `content/exercises.csv` (tus URLs, imágenes y textos, por idioma).
- El sistema **rota** el contenido y no repite: `state/posted_log.json` recuerda lo publicado.
- Los **textos** salen de plantillas por idioma en `config/templates.json`.
- Los **IDs** (page_id, ig_user_id) están en `config/accounts.json`. Los **tokens** son secretos (nunca en el repo).

### Estructura
```
config/
  accounts.json          IDs de Páginas FB y cuentas IG por idioma (NO secreto)
  templates.json         plantillas de caption por tipo e idioma
  secrets.example.json   plantilla de tokens -> copia a secrets.json (local)
content/
  articles.csv           pool de artículos del blog por idioma
  exercises.csv          pool de ejercicios por idioma
src/                     lógica (config, contenido, estado, facebook, instagram)
publish_facebook.py      pipeline FB (--type article | exercise)
publish_instagram.py     pipeline IG
.github/workflows/       programación 24/7 en la nube
state/posted_log.json    registro de rotación (se crea solo)
```

---

## 2. Requisitos previos (una sola vez)

### 2.1 Convierte las 7 cuentas de Instagram a Profesional
En la app de Instagram: **Configuración → Cuenta → Cambiar a cuenta profesional** (Business o Creator). Es gratis e instantáneo. Sin esto, la API oficial no puede publicar.

### 2.2 Crea una App en Meta
1. Ve a <https://developers.facebook.com/apps> → **Crear app** → tipo **Business**.
2. Añade los productos: **Facebook Login** e **Instagram** (API con Instagram Login).

### 2.3 Consigue los tokens de Facebook (1 por Página)
Necesitas un **token de Página** por cada una de las 7 Páginas. Como están en **2 cuentas FB distintas**, repite el proceso iniciando sesión con cada cuenta dueña de esas Páginas:
1. En **Graph API Explorer** elige tu app, pide permisos `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`.
2. Genera un **User Access Token**, y con él lista `/me/accounts` para obtener el `page_id` y el **token de cada Página**.
3. (Recomendado) Conviértelos en **tokens de larga duración** (los de Página derivados de un user token de larga duración no caducan). Guía: "Long-Lived Tokens" en la doc de Meta.

Anota el `page_id` de cada idioma (va en `accounts.json`) y su token (va en los secretos como `FB_TOKEN_<IDIOMA>`).

### 2.4 Consigue los tokens de Instagram (1 por cuenta)
Con **Instagram API con Instagram Login**, cada cuenta profesional autoriza tu app y te da un token:
1. Configura el flujo de **Instagram Login** en tu app (Business Login for Instagram).
2. Cada cuenta autoriza → obtienes un **token de corta duración** → cámbialo por uno de **larga duración (60 días, renovable)**.
3. Con ese token, `GET /me?fields=user_id` te da el **ig_user_id** de la cuenta.

Anota el `ig_user_id` de cada idioma (va en `accounts.json`) y su token (secreto `IG_TOKEN_<IDIOMA>`).

> Alternativa si prefieres vincular cada IG a su Página FB: usa la Instagram Graph API clásica (host `graph.facebook.com`). Para ello pon en el entorno `IG_HOST=https://graph.facebook.com/v21.0` y usa como token el de la Página vinculada.

---

## 3. Rellena tu configuración

1. **`config/accounts.json`** — cambia los códigos de idioma a los tuyos y pon cada `page_id` e `ig_user_id`.
2. **`content/articles.csv`** y **`content/exercises.csv`** — sustituye las filas de ejemplo por tus URLs reales. Columnas:
   `language,title,summary,url,image_url,hashtags`
   - **`image_url` debe ser una URL PÚBLICA** (jpg/png). Instagram no admite subir archivos locales; normalmente la imagen de tu web (og:image del artículo/ejercicio) ya sirve.
   - Puedes poner **varias filas por idioma**: el sistema irá rotando entre ellas.
3. **`config/templates.json`** — ajusta los textos por idioma. Variables: `{title} {summary} {url} {hashtags}`.

---

## 4. Prueba en local (sin publicar)

No hace falta Python en la nube, pero para probar en tu PC instala Python 3.11+ y:
```powershell
pip install -r requirements.txt
python publish_facebook.py --type article --dry-run
python publish_facebook.py --type exercise --dry-run
python publish_instagram.py --dry-run
```
`--dry-run` muestra qué publicaría (y avanza la rotación) sin llamar a las APIs.
Añade `--only es` para probar un solo idioma.

Para una publicación **real de prueba** en un solo idioma:
```powershell
# crea config/secrets.json a partir de config/secrets.example.json con tus tokens
python publish_instagram.py --only es
```

---

## 5. Despliegue 24/7 (GitHub Actions)

Repositorio: **`thibaud1010/ppf11-auto-publish-fb-ig`**.

1. Sube esta carpeta a GitHub y hazla **PÚBLICA**. Es obligatorio: las imágenes de
   los ejercicios y de los artículos FR se sirven desde este repo vía **jsDelivr**
   (`https://cdn.jsdelivr.net/gh/thibaud1010/ppf11-auto-publish-fb-ig@main/...`), que
   solo funciona con repos públicos. El fichero `config/secrets.json` **no sube**
   (está en `.gitignore`); los tokens viven cifrados como secreto (paso 2).
2. En **Settings → Secrets and variables → Actions → New repository secret** crea:
   - **`TOKENS_JSON`** — el contenido de tu `secrets.json` (JSON con los 11 tokens: 7 `FB_TOKEN_*` + 4 `IG_TOKEN_*`; las cuentas IG en modo `page` reutilizan el token de su Página FB).
   - **`GH_PAT`** — un Personal Access Token (fine-grained) con permiso **Secrets: Read and write**
     sobre este repo. Solo lo usa el workflow de renovación para reescribir `TOKENS_JSON`.
3. **Horarios** (ya configurados): **07:00 y 18:00 hora de París**, todo el año.
   El cron de GitHub es en **UTC** y no cambia con el horario de verano, así que cada
   workflow dispara en las horas UTC posibles y un **"guardián"** deja pasar solo la que
   coincide con la hora real de París:
   - `facebook-article.yml` → 07:00 París (artículo)
   - `facebook-exercise.yml` → 18:00 París (ejercicio)
   - `instagram.yml` → 07:00 y 18:00 París (ejercicios)
   - `refresh-tokens.yml` → renueva los tokens IG cada lunes (automático).
4. Los workflows publican y guardan `state/posted_log.json` (la rotación) de vuelta en el
   repo automáticamente. Puedes lanzarlos a mano con **Run workflow** (workflow_dispatch)
   para probar — en modo manual el guardián no aplica y siempre publica.

### Alternativa: VPS con cron
```cron
0 9  * * *  cd /ruta && python3 publish_facebook.py --type article
0 18 * * *  cd /ruta && python3 publish_facebook.py --type exercise
0 12 * * *  cd /ruta && python3 publish_instagram.py
0 20 * * *  cd /ruta && python3 publish_instagram.py
```

---

## 6. Notas importantes

- **Tokens caducan**: los de Instagram duran 60 días (renovables); renueva antes de que expiren. Los de Página FB derivados de un user token de larga duración no caducan.
- **Imágenes públicas obligatorias** para Instagram (URL accesible).
- **Límites de la API**: Instagram permite ~50 publicaciones/cuenta/24h; vas muy por debajo.
- **Añadir contenido**: solo edita los CSV. **Añadir un idioma/cuenta**: añade su bloque en `accounts.json`, sus filas en los CSV, su plantilla y sus tokens `FB_TOKEN_<X>` / `IG_TOKEN_<X>`.
