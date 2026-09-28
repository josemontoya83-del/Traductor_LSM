"""
probar_prediccion.py
Validación de punta a punta: carga una secuencia real de MSL-150,
la pasa por el modelo original, y confirma si predice la clase correcta.
"""
import numpy as np
import tf_keras as keras
from pathlib import Path

MODELO_PATH = "Modelo_ia/LSTM_128_128.h5"
DICCIONARIO_PATH = "Modelo_ia/terms_msl150.txt"
SECUENCIA_PATH = "C:/MSL-150-Dataset/data/sample_npy/hoy/1"
SEÑA_ESPERADA = "hoy"


def cargar_secuencia(carpeta_repeticion: str) -> np.ndarray:
    carpeta = Path(carpeta_repeticion)
    frames = [np.load(carpeta / f"{i}.npy") for i in range(30)]
    secuencia = np.stack(frames)
    assert secuencia.shape == (30, 226), f"Shape inesperado: {secuencia.shape}"
    return secuencia


def cargar_diccionario(ruta: str) -> list[str]:
    with open(ruta, "r", encoding="utf-8") as f:
        return [linea.strip() for linea in f if linea.strip()]


if __name__ == "__main__":
    diccionario = cargar_diccionario(DICCIONARIO_PATH)
    print(f"Diccionario cargado: {len(diccionario)} clases")
    print(f"Índice esperado de '{SEÑA_ESPERADA}':", diccionario.index(SEÑA_ESPERADA))

    modelo = keras.models.load_model(MODELO_PATH)
    secuencia = cargar_secuencia(SECUENCIA_PATH)

    entrada = np.expand_dims(secuencia, axis=0)  # (1, 30, 226) — el modelo espera un batch
    predicciones = modelo.predict(entrada, verbose=0)

    indice_predicho = int(np.argmax(predicciones[0]))
    confianza = float(predicciones[0][indice_predicho])

    print(f"\nÍndice predicho: {indice_predicho}")
    print(f"Palabra predicha: {diccionario[indice_predicho]}")
    print(f"Confianza: {confianza:.4f}")
    print(f"\n¿Coincide con '{SEÑA_ESPERADA}'? {'✅ SÍ' if diccionario[indice_predicho] == SEÑA_ESPERADA else '❌ NO'}")

