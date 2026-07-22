# Guía de estilo — CUERPO de los captions (PPF11)

Redactas el **cuerpo** del caption de cada ejercicio/artículo. NO escribas enlaces, ni hashtags, ni "enlace en la bio": eso se añade luego por código. Solo el cuerpo.

## Reglas de voz (para TODOS)
- **Nativo** en el idioma de la fila (no traducción literal). Usa el **término futbolístico correcto** de ese país (ej. transición/transition/Umschalten/transizione/omschakeling; explosividad/explosiveness/Explosivität…).
- **Tuteo** siempre (te/tú, tu, du, je…).
- **Fiel al contenido original** (usa la columna `description`): mismo montaje, misma acción, mismos datos. Nada de inventar cifras.
- **Tono del contenido**: instructivo y técnico para ejercicios; de gestión/reflexión o físico según el artículo. NUNCA gancho de marketing tipo "el fútbol moderno se gana en…".
- Longitud **~45-90 palabras**. Escaneable. Emojis con medida (ver abajo).
- Empieza SIEMPRE con **⚽** (balón), no con otro emoji.

## Formato del cuerpo de EJERCICIO (4 partes)
1. `⚽ ` + UNA frase que presenta la idea y las cualidades que trabaja. Ej. plantilla: *"⚽ Una idea de ejercicio para trabajar {cualidad 1} y {cualidad 2}."* (deriva las cualidades del `category` y del objetivo del ejercicio).
2. Desarrollo: montaje/zona + acción + cambio de rol, fiel a `description`, en 1-3 frases.
3. Objetivo físico: *"Trabajas {reflejo/velocidad de reacción/explosividad/…}"* — qué se entrena.
4. `🎯 ` + puntuación y volumen SI aparecen en `description` (ej. "🎯 1 punto por gol · 2 si el defensor recupera. Volumen: 4-5 por rol."). Si no hay puntuación/volumen en los datos, OMITE esta línea.

### Ejemplo APROBADO (es) — cuerpo de ejercicio
```
⚽ Una idea de ejercicio para trabajar la transición defensiva y la velocidad de reacción.
En un 15×15 con una miniportería en cada lado, un atacante encara al defensor para regatear y marcar. En cuanto marca o pierde el balón, entra un nuevo atacante y el que atacaba pasa a defender: debe reaccionar al instante para evitar el gol.
Trabajas el reflejo de transición, la velocidad de reacción y la explosividad en el cambio de rol.
🎯 1 punto por gol · 2 si el defensor recupera. Volumen: 4-5 por rol.
```

## Formato del cuerpo de ARTÍCULO (2-3 partes)
1. `⚽ ` + UNA frase que presenta el tema del artículo (puede ser afirmación o pregunta que engancha).
2. Desarrollo: la sustancia/valor del artículo, fiel a `description`, con el tono del contenido (gestión/reflexión o físico/técnico según el tema/`category`).
3. (Opcional) una frase o pregunta breve que invite a leer (ej. "¿Cuántas dominas ya?").

### Ejemplo APROBADO (es) — cuerpo de artículo de gestión
```
⚽ 10 cualidades que separan a un buen entrenador de uno que de verdad deja huella en sus jugadores.
Más allá del sistema táctico, algo marca la diferencia: saber escuchar, crear vínculo, gestionar bien el vestuario. Inspiradas en «La caja de herramientas del entrenador» de F. Ducasse, estas 10 cualidades te ayudarán a gestionar mejor a tu equipo, dentro y fuera del campo.
¿Cuántas dominas ya como entrenador?
```

### Ejemplo APROBADO (es) — cuerpo de artículo físico/técnico
```
⚽ Fuerza y carrera en la misma sesión: así funciona el intermitente-fuerza.
El trabajo intermitente alterna esfuerzos intensos y cortos con periodos de recuperación para desarrollar la potencia aeróbica máxima (PAM). ¿La clave? Que no todo sea correr: puedes meter ejercicios de fuerza dentro del intermitente. Te dejamos la progresión de Cometti, los tiempos de esfuerzo-recuperación y 12 ejercicios listos para tu próxima sesión.
```

## Qué NO incluir
- NO enlaces ni URLs ni dominios. NO "enlace en la bio". NO hashtags. NO "descripción completa en…". Todo eso lo añade el código.
- NO empieces con gancho de marketing. NO uses "¡", exclamaciones excesivas ni superlativos vacíos.

## Salida
Escribe un JSON `{ "<image_url>": "<cuerpo>", ... }` con una entrada por fila (clave = valor EXACTO de la columna `image_url`). Los saltos de línea del cuerpo van como `\n`. Nada más.
