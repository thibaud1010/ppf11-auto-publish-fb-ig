"""Variante de un reel con RÓTULO en el idioma de la cuenta (ffmpeg).

PRUEBA (2026-10-13, solo `es`): hoy las 6 cuentas reciben el MISMO mp4. Aquí se
genera un archivo propio para la cuenta: lienzo vertical 1080x1920 + el título
del reel (config/reels.json -> titles[idioma]) sobreimpreso arriba durante todo
el vídeo. Se activa por cuenta con el flag "reels_variant" en config/accounts.json.

Necesita `ffmpeg` en el PATH (el workflow lo instala).
"""
import os
import re
import shutil
import subprocess
import tempfile
import textwrap

STYLE = "v2"   # cambia al tocar el diseño -> nombre de archivo nuevo en el bucket

W, H = 1080, 1920
BAND_Y = 280            # por debajo de la zona que tapa la interfaz de Reels
PAD = 28
HEAD = {"size": 62, "wrap": 22, "color": "white"}
SUB = {"size": 46, "wrap": 32, "color": "0xFFD60A"}
LINE_GAP = 14

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # runner ubuntu
    "C:/Windows/Fonts/arialbd.ttf",                           # prueba local
]


def title_lines(title):
    """'⚽ Tema: gancho' -> [(linea, estilo), ...] con el tema en mayúsculas."""
    text = re.sub(r"^[^\w¿¡]+", "", title).strip()
    head, _, sub = text.partition(": ")
    # v2 (2026-10-28): solo el tema en blanco; el gancho (frase amarilla) ya no se pinta
    return [(l, HEAD) for l in textwrap.wrap(head.upper(), HEAD["wrap"])]


def build_variant(src, dest, title):
    """Renderiza `src` con el rótulo `title` en `dest`. Devuelve `dest`."""
    font = next((f for f in FONTS if os.path.exists(f)), None)
    if not font:
        raise RuntimeError("no hay fuente para el rótulo (instala fonts-dejavu-core)")
    lines = title_lines(title)
    if not lines:
        raise RuntimeError(f"título vacío: {title!r}")

    # ffmpeg corre DENTRO de un directorio temporal con rutas relativas: así ni la
    # fuente ni los textos necesitan escapado (dos puntos de C:, comillas, etc.).
    work = tempfile.mkdtemp(prefix="reelvar_")
    try:
        shutil.copy(font, os.path.join(work, "font.ttf"))
        band_h = (2 * PAD + sum(st["size"] for _, st in lines)
                  + LINE_GAP * (len(lines) - 1))
        vf = [
            f"scale={W}:{H}:force_original_aspect_ratio=decrease",
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
            "setsar=1",
            f"drawbox=x=0:y={BAND_Y}:w=iw:h={band_h}:color=black@0.6:t=fill",
        ]
        y = BAND_Y + PAD
        for i, (line, st) in enumerate(lines):
            with open(os.path.join(work, f"l{i}.txt"), "w", encoding="utf-8") as f:
                f.write(line)
            vf.append(f"drawtext=fontfile=font.ttf:textfile=l{i}.txt:"
                      f"fontsize={st['size']}:fontcolor={st['color']}:"
                      f"x=(w-text_w)/2:y={y}")
            y += st["size"] + LINE_GAP
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", os.path.abspath(src),
               "-vf", ",".join(vf),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", os.path.abspath(dest)]
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"ffmpeg {p.returncode}: {p.stderr[-300:]}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return dest
