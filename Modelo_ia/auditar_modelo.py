import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"  # fuerza a usar Keras 2 (tf-keras) en vez de Keras 3

import tensorflow as tf

MODELO = "Modelo_ia/LSTM_128_128.h5"

modelo = tf.keras.models.load_model(MODELO)

print("=== INPUT SHAPE ===")
print(modelo.input_shape)

print("\n=== OUTPUT SHAPE (num. de clases) ===")
print(modelo.output_shape)

print("\n=== RESUMEN COMPLETO DE CAPAS ===")
modelo.summary()
