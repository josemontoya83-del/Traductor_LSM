"""
captura_dataset_tramites.py
Graba secuencias de señas propias de trámites UABC, en el mismo formato
de keypoints usado por MSL-150 (226 = 63 mano_der + 63 mano_izq + 100 pose).
Cada repetición se guarda como UN archivo .npy con shape (30, 226).
"""
import os
import cv2
import numpy as np
import mediapipe as mp

SEQ_LEN = 30
DATA_DIR = "dataset_tramites"

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
POSE_UPPER_BODY_IDX = list(range(25))


def extraer_keypoints_msl150(results) -> np.ndarray:
    def mano(landmarks):
        if landmarks:
            return np.array([[p.x, p.y, p.z] for p in landmarks.landmark]).flatten()
        return np.zeros(21 * 3)

    def pose_superior(landmarks):
        if landmarks:
            puntos = [landmarks.landmark[i] for i in POSE_UPPER_BODY_IDX]
            return np.array([[p.x, p.y, p.z, p.visibility] for p in puntos]).flatten()
        return np.zeros(25 * 4)

    mano_der = mano(results.right_hand_landmarks)
    mano_izq = mano(results.left_hand_landmarks)
    pose = pose_superior(results.pose_landmarks)
    vector = np.concatenate([mano_der, mano_izq, pose])
    assert vector.shape[0] == 226
    return vector


def grabar_repeticion(nombre_sena, senante_id, numero_repeticion, holistic, cap) -> str:
    carpeta = os.path.join(DATA_DIR, nombre_sena)
    os.makedirs(carpeta, exist_ok=True)
    secuencia = []

    while len(secuencia) < SEQ_LEN:
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("No se pudo leer de la cámara")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = holistic.process(frame_rgb)

        mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

        cv2.putText(frame, f"{nombre_sena} | frame {len(secuencia)+1}/{SEQ_LEN}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Captura LSM-Connect", frame)

        secuencia.append(extraer_keypoints_msl150(results))

        if cv2.waitKey(1) & 0xFF == ord("q"):
            raise KeyboardInterrupt("Cancelado por el usuario")

    archivo = os.path.join(carpeta, f"{senante_id}_{numero_repeticion:03d}.npy")
    np.save(archivo, np.array(secuencia))
    return archivo


def main():
    nombre_sena = input("Nombre de la seña (ej. beca, kardex, inscripcion): ").strip().lower()
    senante_id = input("Tu identificador (ej. tony, alejandro, diego): ").strip().lower()
    num_repeticiones = int(input("¿Cuántas repeticiones vas a grabar en esta sesión?: "))

    cap = cv2.VideoCapture(0)

    with mp_holistic.Holistic(min_detection_confidence=0.85, min_tracking_confidence=0.25) as holistic:
        for i in range(1, num_repeticiones + 1):
            input(f"\nRepetición {i}/{num_repeticiones} de '{nombre_sena}'. Presiona ENTER cuando estés listo...")
            try:
                archivo = grabar_repeticion(nombre_sena, senante_id, i, holistic, cap)
                print(f"Guardado: {archivo}")
            except KeyboardInterrupt:
                print("Grabación cancelada.")
                break

    cap.release()
    cv2.destroyAllWindows()
    print("\nListo. Revisa la carpeta 'dataset_tramites' y sube los .npy generados.")


if __name__ == "__main__":
    main()