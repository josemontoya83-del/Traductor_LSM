"""
extraer_puntos.py — Saca los puntos de MediaPipe de todos los videos grabados.

    python herramientas/extraer_puntos.py              # solo los videos que aún no tienen puntos
    python herramientas/extraer_puntos.py --rehacer    # todos (p. ej. si cambió lsm/puntos.py)

Lee datos/videos/**/<clip>.mp4 o .webm y escribe datos/puntos/**/<clip>.npz con el MISMO extractor
que usa el servidor en vivo (lsm/puntos.py). Los tiempos de cada cuadro salen del .json que
guardó la captura clásica o, en los videos del navegador, de la marca de tiempo de cada cuadro
(las cámaras web no siempre van a fps constante).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from lsm import puntos as P  # noqa: E402
from lsm.datos import listar_clips  # noqa: E402


def extraer_video(ruta_video: Path, tiempos=None, holistic=None) -> dict:
    cerrar = holistic is None
    holistic = holistic or P.crear_holistic()
    cap = cv2.VideoCapture(str(ruta_video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cuadros, msegs = [], []
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            msegs.append(cap.get(cv2.CAP_PROP_POS_MSEC))
            cuadros.append(P.procesar_imagen(holistic, frame))
    finally:
        cap.release()
        if cerrar:
            holistic.close()
    marcas = np.asarray(msegs, np.float64) / 1000
    if tiempos is not None and len(tiempos) >= len(cuadros):
        t = np.asarray(tiempos[:len(cuadros)], np.float64)          # captura clásica: tiempos exactos
    elif len(marcas) > 1 and np.all(np.diff(marcas) > 0):
        t = marcas - marcas[0]                                       # navegador (.webm): marca de cada cuadro
    else:
        t = np.arange(len(cuadros)) / (fps if 1 <= fps <= 120 else 30)
    return P.apilar(cuadros, t)


def necesita(clip, rehacer: bool) -> bool:
    if rehacer or not clip.puntos.exists():
        return True
    with np.load(clip.puntos) as z:
        return str(z["version"]) != P.VERSION_EXTRACTOR


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rehacer", action="store_true")
    a = ap.parse_args()
    clips = [c for c in listar_clips() if c.video.exists() and necesita(c, a.rehacer)]
    if not clips:
        print("No hay videos nuevos que procesar.")
        return
    print(f"Procesando {len(clips)} videos...")
    t0 = time.time()
    for i, clip in enumerate(clips, 1):
        # Holistic nuevo por video: el seguimiento de un video no debe "contaminar" al siguiente.
        datos = extraer_video(clip.video, clip.meta.get("tiempos"))
        clip.puntos.parent.mkdir(parents=True, exist_ok=True)
        P.guardar(clip.puntos, datos)
        mano = float(np.mean([P.hay_mano(P.cuadro(datos, j)) for j in range(len(datos["t"]))] or [0]))
        print(f"  [{i}/{len(clips)}] {clip.persona}/s{clip.sesion}/{clip.json.stem}: "
              f"{len(datos['t'])} cuadros, mano en {mano:.0%}")
    print(f"Listo en {time.time() - t0:.0f} s.")


if __name__ == "__main__":
    main()
