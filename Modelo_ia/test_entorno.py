import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import cv2
import mediapipe as mp
import tensorflow as tf

# --- Paso 1: Cargar el modelo ---
print("Cargando modelo LSTM_128_128...")

ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_modelo = os.path.join(ruta_script, "LSTM_128_128.h5")
modelo = tf.keras.models.load_model(ruta_modelo)

print("Modelo cargado correctamente.")
print("Forma de entrada esperada:", modelo.input_shape)

# --- Paso 2: Configurar MediaPipe Holistic ---
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

# --- Paso 3: Abrir la cámara ---
cap = cv2.VideoCapture(0)

with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("No se pudo leer la cámara.")
            break

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultados = holistic.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        mp_drawing.draw_landmarks(image, resultados.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        mp_drawing.draw_landmarks(image, resultados.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        mp_drawing.draw_landmarks(image, resultados.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

        cv2.imshow('Prueba de entorno - LSM Connect', image)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()