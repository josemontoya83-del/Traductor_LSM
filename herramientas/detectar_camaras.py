"""
detectar_camaras.py — Lista las cámaras conectadas.

    python herramientas/detectar_camaras.py
"""
import platform

import cv2


def _abrir(indice: int):
    api = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
    return cv2.VideoCapture(indice, api)


def camaras_disponibles(maximo: int = 6) -> list[tuple[int, int, int]]:
    """-> [(índice, ancho, alto)] de las cámaras que entregan imagen."""
    encontradas = []
    for i in range(maximo):
        cap = _abrir(i)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                encontradas.append((i, frame.shape[1], frame.shape[0]))
        cap.release()
    return encontradas


def primera_camara_disponible():
    camaras = camaras_disponibles()
    return camaras[0][0] if camaras else None


if __name__ == "__main__":
    camaras = camaras_disponibles()
    if not camaras:
        print("No se encontró ninguna cámara.")
    for i, w, h in camaras:
        print(f"Cámara {i}: {w}x{h}")
    if camaras:
        print(f"\nSe usará la cámara {camaras[0][0]}. Para otra: --camara N")
