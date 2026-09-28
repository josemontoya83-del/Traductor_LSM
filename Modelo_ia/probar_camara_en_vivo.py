"""
probar_camara_en_vivo.py
Captura 30 frames en vivo desde la cámara, extrae keypoints en el
formato exacto de MSL-150 (226 = 63 mano_der + 63 mano_izq + 100 pose),
y corre la predicción con el modelo original para confirmar que el
pipeline en vivo es compatible con el que ya validamos con datos MSL-150.
"""
import cv2
import numpy as np
import mediapipe as mp
import tf_keras as keras

MODELO_PATH = "Modelo_ia/LSTM_128_128.h5"
DICCIONARIO_PATH = "Modelo_ia/terms_msl150.txt"
SEQ_LEN = 30

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

# Índices 0-24 de MediaPipe Pose = tren superior (excluye índices 25-32)
POSE_UPPER_BODY_IDX = list(range(25))


def extraer_keypoints_msl150(results) -> np.ndarray:
    """Vector de 226 floats: mano_der(63) + mano_izq(63) + pose(100). Mismo formato que MSL-150."""

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
    assert vector.shape[0] == 226, f"Shape incorrecto: {vector.shape[0]}"
    return vector


def cargar_diccionario(ruta: str) -> list[str]:
    with open(ruta, "r", encoding="utf-8") as f:
        return [linea.strip() for linea in f if linea.strip()]


def main():
    diccionario = cargar_diccionario(DICCIONARIO_PATH)
    modelo = keras.models.load_model(MODELO_PATH)

    cap = cv2.VideoCapture(0)
    secuencia = []

    print(f"Grabando {SEQ_LEN} frames... haz cualquier movimiento con las manos frente a la cámara.")
    print("Presiona 'q' para cancelar en cualquier momento.\n")

    with mp_holistic.Holistic(
        min_detection_confidence=0.85,
        min_tracking_confidence=0.25,
    ) as holistic:
        while len(secuencia) < SEQ_LEN:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("No se pudo leer de la cámara")

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = holistic.process(frame_rgb)

            mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

            cv2.putText(frame, f"Frame {len(secuencia)+1}/{SEQ_LEN}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Captura - probar_camara_en_vivo", frame)

            secuencia.append(extraer_keypoints_msl150(results))

            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Cancelado por el usuario.")
                cap.release()
                cv2.destroyAllWindows()
                return

    cap.release()
    cv2.destroyAllWindows()

    entrada = np.expand_dims(np.array(secuencia), axis=0)  # (1, 30, 226)
    assert entrada.shape == (1, 30, 226), f"Shape final inesperado: {entrada.shape}"

    predicciones = modelo.predict(entrada, verbose=0)
    indice_predicho = int(np.argmax(predicciones[0]))
    confianza = float(predicciones[0][indice_predicho])

    print(f"\nShape de la secuencia capturada: {entrada.shape}  (correcto: coincide con lo esperado)")
    print(f"Palabra predicha: {diccionario[indice_predicho]}")
    print(f"Confianza: {confianza:.4f}")
    print("\n(No esperamos que acierte una seña médica real — solo confirmamos que el")
    print(" pipeline en vivo produce el mismo formato de datos que validamos con MSL-150.)")


if __name__ == "__main__":
    main()


