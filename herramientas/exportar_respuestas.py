"""
exportar_respuestas.py — Copia las respuestas del empleado grabadas en LSM (bloque G) a la
interfaz, para que el alumno las vea en video.

    python herramientas/exportar_respuestas.py --persona P03
    python herramientas/exportar_respuestas.py --persona P03 --solo pase_caja,regrese_manana

Convierte cada video a H.264 (el formato que reproducen los navegadores; el de la captura no)
y lo deja en Frontend/lsm-connect/public/respuestas/<id>.mp4. Usa el ffmpeg que trae el
paquete imageio-ffmpeg (no hay que instalar nada aparte).
Solo exportar videos de personas que hayan aceptado, en el consentimiento, que su video
se muestre en la ventanilla.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lsm.config import RAIZ  # noqa: E402
from lsm.datos import listar_clips  # noqa: E402

DESTINO = RAIZ / "Frontend" / "lsm-connect" / "public" / "respuestas"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--solo", help="ids separados por coma")
    a = ap.parse_args()
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    solo = set(a.solo.split(",")) if a.solo else None
    clips = [c for c in listar_clips(["respuesta"]) if c.persona == a.persona.upper()
             and (solo is None or c.etiqueta in solo)]
    if not clips:
        raise SystemExit("No hay respuestas grabadas (bloque G) para esa persona.")
    DESTINO.mkdir(parents=True, exist_ok=True)
    elegidos = {}
    for c in clips:  # si hay varias tomas de la misma respuesta, gana la última
        elegidos[c.etiqueta] = c
    for etiqueta, c in sorted(elegidos.items()):
        salida = DESTINO / f"{etiqueta}.mp4"
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(c.video), "-an", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-vf", "scale=-2:480", "-movflags", "+faststart", str(salida)],
                       check=True)
        print(f"  {etiqueta}: {salida}")
    print("Listo. La interfaz los muestra al tocar la respuesta rápida correspondiente.")


if __name__ == "__main__":
    main()
