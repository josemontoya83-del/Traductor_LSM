import tf_keras as keras  # usamos tf_keras directo, sin pasar por tf.keras

MODELO = "Modelo_ia/LSTM_128_128.h5"

modelo = keras.models.load_model(MODELO)

print("=== INPUT SHAPE ===")
print(modelo.input_shape)

print("\n=== OUTPUT SHAPE (num. de clases) ===")
print(modelo.output_shape)

print("\n=== RESUMEN COMPLETO DE CAPAS ===")
modelo.summary()    