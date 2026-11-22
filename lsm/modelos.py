"""Construcción, guardado y carga de los dos modelos (letras y señas)."""
from __future__ import annotations

import json
import warnings
from pathlib import Path

from .config import DIR_MODELOS
from .puntos import VERSION_EXTRACTOR

VERSION_RASGOS = "v1"


def _keras():
    import tf_keras as keras

    return keras


def construir_letras(forma_entrada: tuple, n_clases: int):
    """Ventana corta (8 cuadros x 66) -> letra. Una red densa basta: la forma de la mano ya viene
    normalizada y la ventana captura el movimiento de J, Z, Ñ..."""
    keras = _keras()
    L = keras.layers
    entrada = keras.Input(forma_entrada)
    x = L.Flatten()(entrada)
    x = L.Dense(256, activation="relu")(x)
    x = L.Dropout(0.3)(x)
    x = L.Dense(128, activation="relu")(x)
    x = L.Dropout(0.3)(x)
    salida = L.Dense(n_clases, activation="softmax")(x)
    modelo = keras.Model(entrada, salida, name="lsm_letras")
    modelo.compile(keras.optimizers.Adam(1e-3), "sparse_categorical_crossentropy", ["accuracy"])
    return modelo


def construir_senas(forma_entrada: tuple, n_clases: int):
    """Secuencia (hasta 90 cuadros x rasgos, con relleno de ceros) -> seña."""
    keras = _keras()
    L = keras.layers
    entrada = keras.Input(forma_entrada)
    x = L.Masking(0.0)(entrada)
    x = L.GRU(128, return_sequences=True, dropout=0.2)(x)
    x = L.GRU(96, dropout=0.2)(x)
    x = L.Dropout(0.4)(x)
    x = L.Dense(96, activation="relu")(x)
    salida = L.Dense(n_clases, activation="softmax")(x)
    modelo = keras.Model(entrada, salida, name="lsm_senas")
    modelo.compile(keras.optimizers.Adam(1e-3), "sparse_categorical_crossentropy", ["accuracy"])
    return modelo


def guardar(modelo, nombre: str, meta: dict, carpeta: Path = DIR_MODELOS) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.h5"
    with warnings.catch_warnings():  # .h5 a propósito: es el formato que ya usaba el proyecto
        warnings.simplefilter("ignore")
        modelo.save(ruta)
    meta = dict(meta, version_extractor=VERSION_EXTRACTOR, version_rasgos=VERSION_RASGOS)
    (carpeta / f"{nombre}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def existe(nombre: str, carpeta: Path = DIR_MODELOS) -> bool:
    return (carpeta / f"{nombre}.h5").exists() and (carpeta / f"{nombre}.json").exists()


def cargar(nombre: str, carpeta: Path = DIR_MODELOS):
    """-> (modelo, meta). Avisa si el modelo se entrenó con otra versión de puntos/rasgos."""
    meta = json.loads((carpeta / f"{nombre}.json").read_text(encoding="utf-8"))
    if meta.get("version_extractor") != VERSION_EXTRACTOR or meta.get("version_rasgos") != VERSION_RASGOS:
        raise RuntimeError(
            f"El modelo '{nombre}' se entrenó con otra versión de puntos/rasgos "
            f"({meta.get('version_extractor')}, {meta.get('version_rasgos')}). Vuelve a extraer y entrenar.")
    modelo = _keras().models.load_model(carpeta / f"{nombre}.h5", compile=False)
    return modelo, meta
