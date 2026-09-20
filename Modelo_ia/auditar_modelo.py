import tensorflow as tf

MODELO = "Modelo_ia/LSTM_128_128.h5"  # ajusta la ruta si tu archivo está en otro lugar

modelo = tf.keras.models.load_model(MODELO)

print("=== INPUT SHAPE ===")
print(modelo.input_shape)

print("\n=== OUTPUT SHAPE (num. de clases) ===")
print(modelo.output_shape)

print("\n=== RESUMEN COMPLETO DE CAPAS ===")
modelo.summary()