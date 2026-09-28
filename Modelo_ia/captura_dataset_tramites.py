"""
captura_dataset_tramites.py
Graba secuencias de señas propias de trámites UABC en el mismo formato de
keypoints que MSL-150 (226 por frame). Cada repetición se guarda como UN
archivo .npy con shape (30, 226).

Controles (con la ventana de la cámara seleccionada):
  ESPACIO -> empezar a grabar / detener la grabación
  Q       -> salir
"""
import os
import re
import time

import cv2
import mediapipe as mp
import numpy as np

SEQ_LEN = 30           # frames que espera el modelo
MIN_FRAMES = 10        # menos que esto = grabación demasiado corta, se descarta
MIN_HAND_RATIO = 0.5   # al menos la mitad de los frames deben tener una mano detectada
DATA_DIR = "dataset_tramites"

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
POSE_UPPER_BODY_IDX = list(range(25))


def extraer_keypoints_msl150(results) -> np.ndarray:
    """Vector de 226 floats: mano_der(63) + mano_izq(63) + pose(100)."""

    def mano(landmarks):
        if landmarks:
            return np.array([[p.x, p.y, p.z] for p in landmarks.landmark]).flatten()
        return np.zeros(21 * 3)

    def pose_superior(landmarks):
        if landmarks:
            puntos = [landmarks.landmark[i] for i in POSE_UPPER_BODY_IDX]
            return np.array([[p.x, p.y, p.z, p.visibility] for p in puntos]).flatten()
        return np.zeros(25 * 4)

    vector = np.concatenate([
        mano(results.right_hand_landmarks),
        mano(results.left_hand_landmarks),
        pose_superior(results.pose_landmarks),
    ])
    assert vector.shape[0] == 226
    return vector


def hay_mano(results) -> bool:
    return results.right_hand_landmarks is not None or results.left_hand_landmarks is not None


def remuestrear(secuencia: list, longitud: int = SEQ_LEN) -> np.ndarray:
    """Convierte una secuencia de N frames en exactamente `longitud` frames (índices equiespaciados)."""
    arr = np.array(secuencia)
    indices = np.linspace(0, len(arr) - 1, longitud).round().astype(int)
    return arr[indices]


def siguiente_numero(carpeta: str, senante_id: str) -> int:
    """Continúa la numeración para no sobrescribir grabaciones anteriores del mismo señante."""
    patron = re.compile(rf"^{re.escape(senante_id)}_(\d+)\.npy$")
    numeros = [int(m.group(1)) for f in os.listdir(carpeta) if (m := patron.match(f))]
    return max(numeros, default=0) + 1


def dibujar(frame, results) -> None:
    mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
    mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)


def guardar_si_es_valida(secuencia, frames_con_mano, duracion, carpeta, senante_id, numero) -> bool:
    n = len(secuencia)
    if n < MIN_FRAMES:
        print(f"  Descartada: solo {n} frames (mínimo {MIN_FRAMES}). Graba un poco más.")
        return False
    if frames_con_mano / n < MIN_HAND_RATIO:
        print(f"  Descartada: mano detectada solo en {frames_con_mano}/{n} frames. Revisa luz y encuadre.")
        return False

    archivo = os.path.join(carpeta, f"{senante_id}_{numero:03d}.npy")
    np.save(archivo, remuestrear(secuencia))
    print(f"  Guardado: {archivo}  ({n} frames en {duracion:.1f}s -> {SEQ_LEN} frames)")
    return True


def main() -> None:
    nombre_sena = input("Nombre de la seña (ej. beca, kardex, inscripcion): ").strip().lower()
    senante_id = input("Tu identificador (ej. tony, alejandro, diego): ").strip().lower()
    indice_camara = int(input("Índice de cámara (0 = laptop; revisa con detectar_camaras.py) [0]: ") or 0)

    carpeta = os.path.join(DATA_DIR, nombre_sena)
    os.makedirs(carpeta, exist_ok=True)
    numero = siguiente_numero(carpeta, senante_id)

    cap = cv2.VideoCapture(indice_camara, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la cámara con índice {indice_camara}")

    grabando = False
    secuencia, frames_con_mano, inicio = [], 0, 0.0

    print("\nHaz clic en la ventana de la cámara. ESPACIO = empezar/detener, Q = salir.\n")

    with mp_holistic.Holistic(min_detection_confidence=0.85, min_tracking_confidence=0.25) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer de la cámara.")
                break

            results = holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            dibujar(frame, results)

            if grabando:
                secuencia.append(extraer_keypoints_msl150(results))
                frames_con_mano += hay_mano(results)
                texto = f"GRABANDO ({len(secuencia)} frames) - ESPACIO para detener"
                color = (0, 0, 255)
            else:
                texto = f"'{nombre_sena}' | siguiente: #{numero} | ESPACIO = grabar | Q = salir"
                color = (0, 255, 0)

            cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.imshow("Captura LSM-Connect", frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                break
            if tecla == 32:  # ESPACIO
                if not grabando:
                    grabando, secuencia, frames_con_mano, inicio = True, [], 0, time.time()
                else:
                    grabando = False
                    duracion = time.time() - inicio
                    if guardar_si_es_valida(secuencia, frames_con_mano, duracion, carpeta, senante_id, numero):
                        numero += 1

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nListo. Grabaciones en: {carpeta}")


if __name__ == "__main__":
    main() 