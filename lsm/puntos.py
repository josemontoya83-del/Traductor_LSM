"""
Extracción de puntos (keypoints) con MediaPipe Holistic.

Un "cuadro" es un dict con los puntos de UNA imagen:
    mano_der (21, 3)   mano derecha DE LA PERSONA (x, y, z)
    mano_izq (21, 3)   mano izquierda de la persona
    pose     (33, 4)   cuerpo (x, y, z, visibilidad)
    cara     (132, 3)  subconjunto de la malla facial: labios, cejas, ojos, contorno y nariz
Un "clip" es el mismo dict pero con un eje de tiempo delante (T, ...), más "t" (segundos).

Lo que falta (mano no detectada, etc.) se guarda como ceros.

Coordenadas: x e y van en "anchos de imagen" (y se multiplica por alto/ancho). Así la geometría
no cambia entre un video 16:9 de la captura y la cámara 4:3 del navegador.

IMPORTANTE: la captura, la extracción offline y el servidor usan estas MISMAS funciones y
parámetros. Si se cambian, se sube VERSION_EXTRACTOR y hay que volver a correr extraer_puntos.
"""
from __future__ import annotations

import numpy as np

VERSION_EXTRACTOR = "holistic-0.10.13-c1-w640-v1"
ANCHO_PROCESO = 640  # toda imagen se reduce a este ancho antes de MediaPipe (igual en vivo y offline)
PARAMS_HOLISTIC = dict(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    refine_face_landmarks=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

N_MANO, N_POSE = 21, 33
# Labios, cejas, ojos, óvalo de la cara y nariz (calculado de las conexiones de FaceMesh).
CARA_IDX = (
    0, 1, 4, 6, 7, 10, 13, 14, 17, 21, 33, 37, 39, 40, 46, 52, 53, 54, 55, 58, 61, 63, 65, 66, 67,
    70, 78, 80, 81, 82, 84, 87, 88, 91, 93, 95, 103, 105, 107, 109, 127, 132, 133, 136, 144, 145,
    146, 148, 149, 150, 152, 153, 154, 155, 157, 158, 159, 160, 161, 162, 163, 168, 172, 173, 176,
    178, 181, 185, 191, 234, 246, 249, 251, 263, 267, 269, 270, 276, 282, 283, 284, 285, 288, 291,
    293, 295, 296, 297, 300, 308, 310, 311, 312, 314, 317, 318, 321, 323, 324, 332, 334, 336, 338,
    356, 361, 362, 365, 373, 374, 375, 377, 378, 379, 380, 381, 382, 384, 385, 386, 387, 388, 389,
    390, 397, 398, 400, 402, 405, 409, 415, 454, 466,
)
N_CARA = len(CARA_IDX)
FORMAS = {"mano_der": (N_MANO, 3), "mano_izq": (N_MANO, 3), "pose": (N_POSE, 4), "cara": (N_CARA, 3)}
PARTES = tuple(FORMAS)


def crear_holistic():
    import mediapipe as mp

    return mp.solutions.holistic.Holistic(**PARAMS_HOLISTIC)


def preparar(bgr: np.ndarray) -> tuple[np.ndarray, float]:
    """Reduce la imagen a ANCHO_PROCESO y la pasa a RGB. Devuelve (rgb, alto/ancho)."""
    import cv2

    h, w = bgr.shape[:2]
    if w != ANCHO_PROCESO:
        bgr = cv2.resize(bgr, (ANCHO_PROCESO, max(1, round(h * ANCHO_PROCESO / w))),
                         interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), h / w


def vacio() -> dict:
    return {k: np.zeros(f, np.float32) for k, f in FORMAS.items()}


def extraer(resultados, relacion: float) -> dict:
    """Resultados de Holistic -> cuadro. `relacion` = alto/ancho de la imagen."""
    c = vacio()

    def llenar(destino, landmarks, idx=None, vis=False):
        if landmarks is None:
            return
        lm = landmarks.landmark
        puntos = [lm[i] for i in idx] if idx is not None else lm
        for j, p in enumerate(puntos):
            destino[j, 0], destino[j, 1], destino[j, 2] = p.x, p.y * relacion, p.z
            if vis:
                destino[j, 3] = p.visibility

    llenar(c["mano_der"], resultados.right_hand_landmarks)
    llenar(c["mano_izq"], resultados.left_hand_landmarks)
    llenar(c["pose"], resultados.pose_landmarks, vis=True)
    llenar(c["cara"], resultados.face_landmarks, idx=CARA_IDX)
    return c


def procesar_imagen(holistic, bgr: np.ndarray) -> dict:
    rgb, relacion = preparar(bgr)
    return extraer(holistic.process(rgb), relacion)


def apilar(cuadros: list[dict], tiempos=None) -> dict:
    """Lista de cuadros -> clip (T, ...)."""
    clip = {k: (np.stack([c[k] for c in cuadros]).astype(np.float32) if cuadros
                else np.zeros((0, *f), np.float32)) for k, f in FORMAS.items()}
    if tiempos is not None:
        clip["t"] = np.asarray(tiempos, np.float64)
    return clip


def cuadro(clip: dict, i: int) -> dict:
    return {k: clip[k][i] for k in PARTES}


def cuadros(clip: dict) -> list[dict]:
    return [cuadro(clip, i) for i in range(len(clip["pose"]))]


def recortar(clip: dict, ini: int, fin: int) -> dict:
    return {k: v[ini:fin] for k, v in clip.items() if k in PARTES or k == "t"}


def guardar(ruta, clip: dict) -> None:
    np.savez_compressed(ruta, version=VERSION_EXTRACTOR, **{k: clip[k] for k in (*PARTES, "t")})


def cargar(ruta) -> dict:
    with np.load(ruta) as z:
        clip = {k: z[k] for k in (*PARTES, "t")}
        clip["version"] = str(z["version"])
    return clip


def hay_mano(c: dict) -> bool:
    return bool(c["mano_der"].any() or c["mano_izq"].any())


def hay_hombros(c: dict) -> bool:
    return bool(c["pose"][[11, 12], :2].all())
