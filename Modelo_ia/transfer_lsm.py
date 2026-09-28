"""
transfer_lsm.py
Transfer learning desde LSTM_128_128.h5 (MSL-150, vocabulario médico)
hacia el vocabulario de trámites UABC (25-30 clases).
Corte confirmado: después de 'lstm_1' (128 dimensiones), descartando
el cabezal denso especializado en vocabulario médico.
"""
import tf_keras as keras
from tf_keras import layers, Model


def build_transfer_model(base_model_path: str, num_classes: int, freeze_base: bool = True) -> Model:
    base_model = keras.models.load_model(base_model_path)

    # Verificación de compatibilidad (ya confirmada con auditar_modelo.py,
    # la dejamos como salvaguarda por si cambia el modelo base)
    expected_shape = (30, 226)
    if base_model.input_shape[1:] != expected_shape:
        raise ValueError(f"Shape inesperado: {base_model.input_shape[1:]}")

    # Extractor de características: hasta la salida de 'lstm_1' (128-dim)
    feature_extractor = Model(
        inputs=base_model.input,
        outputs=base_model.get_layer("lstm_1").output,
        name="msl150_feature_extractor",
    )
    feature_extractor.trainable = not freeze_base

    inputs = feature_extractor.input
    x = feature_extractor.output
    x = layers.Dropout(0.3, name="dropout_tramites")(x)
    x = layers.Dense(64, activation="relu", name="dense_tramites")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="clasificador_tramites")(x)

    model = Model(inputs, outputs, name="lsm_connect_classifier")
    model.compile(
        optimizer=keras.optimizers.Adam(1e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


if __name__ == "__main__":
    # Prueba rápida: construye el modelo con un vocabulario de ejemplo de 25 clases
    # y muestra el resumen para confirmar que el corte de capas funciona bien.
    modelo_prueba = build_transfer_model(
        base_model_path="Modelo_ia/LSTM_128_128.h5",
        num_classes=25,
        freeze_base=True,
    )
    print("=== MODELO DE TRANSFER LEARNING CONSTRUIDO CORRECTAMENTE ===")
    modelo_prueba.summary() 