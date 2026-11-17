"""
detectar_camaras.py
Busca las cámaras conectadas y elige la primera que realmente entrega imagen.

Uso directo (raíz del repo, venv activo):
    python Modelo_ia/detectar_camaras.py      # lista las cámaras y muestra la elegida 5 s

Desde otros scripts:
    from detectar_camaras import primera_camara_disponible
    indice = primera_camara_disponible()      # None si no hay ninguna
"""
import cv2

MAX_INDICES = 5  # se prueban los índices 0..4


def camara_funciona(indice: int) -> bool:
    """True si la cámara con ese índice abre y entrega al menos un cuadro."""
    cap = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
    try:
        return cap.isOpened() and cap.read()[0]
    finally:
        cap.release()


def camaras_disponibles(max_indices: int = MAX_INDICES) -> list[int]:
    return [i for i in range(max_indices) if camara_funciona(i)]


def primera_camara_disponible(max_indices: int = MAX_INDICES):
    """Índice de la primera cámara que funciona, o None si no hay ninguna."""
    for i in range(max_indices):
        if camara_funciona(i):
            return i
    return None


def main() -> None:
    disponibles = camaras_disponibles()
    for i in range(MAX_INDICES):
        print(f"Índice {i}: {'cámara disponible' if i in disponibles else 'no disponible'}")
    if not disponibles:
        print("No se encontró ninguna cámara. Revisa que esté conectada y que otra app no la esté usando.")
        return
    elegida = disponibles[0]
    print(f"Se usará la cámara {elegida}. (Vista previa por 5 s; cualquier tecla la cierra.)")
    cap = cv2.VideoCapture(elegida, cv2.CAP_DSHOW)
    ok, frame = cap.read()
    cap.release()
    if ok:
        cv2.imshow(f"Camara {elegida}", frame)
        cv2.waitKey(5000)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
