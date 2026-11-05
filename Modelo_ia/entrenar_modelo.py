"""
entrenar_modelo.py  (v2)
Entrena y evalúa el clasificador de trámites de LSM-Connect con dataset_tramites/.

Pipeline: normalizar (preprocesar.py) -> aumento de datos -> modelo (GRU desde cero por
defecto, o fine-tuning completo del LSTM de MSL-150) -> evaluación.

Dos métricas, SIEMPRE las dos:
  1) "mismo grupo": entrena con repeticiones 1-6 y prueba con 7-12 de las mismas personas.
     OPTIMISTA: dice qué tan bien funciona con gente ya vista.
  2) "dejando una persona fuera": entrena con los demás identificadores y prueba con el
     que quedó fuera. Esta es la métrica real para un usuario nuevo en ventanilla.

Uso (raíz del repo, venv activo):
    python Modelo_ia/entrenar_modelo.py                 # evalúa con GRU
    python Modelo_ia/entrenar_modelo.py --modelo finetune
    python Modelo_ia/entrenar_modelo.py --guardar       # además entrena con todo y guarda
"""
import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf
import tf_keras as keras
from tf_keras import layers

from preprocesar import aumentar_secuencia, normalizar_secuencia
from transfer_lsm import build_transfer_model

DATA_DIR = Path("dataset_tramites")
MODELO_BASE = "Modelo_ia/LSTM_128_128.h5"
SALIDA = Path("Modelo_ia")
CLASES = ["inscripcion", "reinscripcion", "kardex", "constancia", "foto", "credencial",
          "documentos", "solicitar", "recoger", "entrega", "si", "no", "duda", "gracias", "reposo"]
PATRON = re.compile(r"^(?P<persona>.+)_(?P<num>\d+)\.npy$")
EPOCAS, SEMILLA, COPIAS_AUMENTO = 80, 42, 8


def fijar_semillas(semilla: int) -> None:
    # No usar keras.utils.set_random_seed: rompe tf_keras 2.17 en Python 3.12.
    random.seed(semilla)
    np.random.seed(semilla)
    tf.random.set_seed(semilla)


def cargar_dataset():
    """Devuelve X normalizado (N,30,226), y (N,), personas (N,), numeros (N,)."""
    X, y, personas, numeros = [], [], [], []
    for clase in CLASES:
        for f in sorted((DATA_DIR / clase).glob("*.npy")):
            m = PATRON.match(f.name)
            seq = np.load(f)
            if m is None or seq.shape != (30, 226):
                continue
            X.append(normalizar_secuencia(seq))
            y.append(CLASES.index(clase))
            personas.append(m["persona"])
            numeros.append(int(m["num"]))
    return np.array(X), np.array(y), np.array(personas), np.array(numeros)


def construir_modelo(tipo: str) -> keras.Model:
    if tipo == "finetune":
        return build_transfer_model(MODELO_BASE, len(CLASES), freeze_base=False)
    entrada = keras.Input((30, 226))
    x = layers.Masking(0.0)(entrada)
    x = layers.GRU(64)(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(64, activation="relu")(x)
    salida = layers.Dense(len(CLASES), activation="softmax")(x)
    modelo = keras.Model(entrada, salida, name="lsm_connect_gru")
    modelo.compile(optimizer=keras.optimizers.Adam(2e-3), loss="categorical_crossentropy",
                   metrics=["accuracy"])
    return modelo


def entrenar(tipo: str, X: np.ndarray, y: np.ndarray) -> keras.Model:
    fijar_semillas(SEMILLA)
    rng = np.random.default_rng(SEMILLA)
    Xa, ya = list(X), list(y)
    for seq, etiqueta in zip(X, y):
        for _ in range(COPIAS_AUMENTO):
            Xa.append(aumentar_secuencia(seq, rng))
            ya.append(etiqueta)
    Xa, ya = np.array(Xa), np.array(ya)
    orden = rng.permutation(len(Xa))
    keras.backend.clear_session()
    modelo = construir_modelo(tipo)
    modelo.fit(Xa[orden], keras.utils.to_categorical(ya[orden], len(CLASES)),
               validation_split=0.15, epochs=EPOCAS, batch_size=32, verbose=0,
               callbacks=[keras.callbacks.EarlyStopping(monitor="val_loss", patience=10,
                                                       restore_best_weights=True)])
    return modelo


def top_k(prob: np.ndarray, y: np.ndarray, k: int = 3) -> float:
    return float(np.mean([y[i] in np.argsort(-prob[i])[:k] for i in range(len(y))]))


def informe(y_real, y_pred, titulo):
    print(f"\n{titulo}: precisión {np.mean(y_real == y_pred):.1%} ({int(np.sum(y_real == y_pred))}/{len(y_real)})")
    por_clase = []
    for i, c in enumerate(CLASES):
        m = y_real == i
        if m.any():
            por_clase.append((np.mean(y_pred[m] == i), c, int(m.sum())))
    print("  Por clase (de menor a mayor):")
    for acc, c, n in sorted(por_clase):
        print(f"    {c:15s} {acc:4.0%} ({n} muestras)")
    conf = Counter((CLASES[a], CLASES[b]) for a, b in zip(y_real, y_pred) if a != b)
    print("  Confusiones más frecuentes (real -> predicho):")
    for (a, b), n in conf.most_common(6):
        print(f"    {a} -> {b}: {n}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", choices=["gru", "finetune"], default="gru")
    ap.add_argument("--guardar", action="store_true")
    a = ap.parse_args()

    X, y, personas, numeros = cargar_dataset()
    print(f"Muestras: {len(X)} | Personas: {sorted(set(personas))} | Clases: {len(CLASES)} | Modelo: {a.modelo}")

    # 1) Mismo grupo (optimista)
    tr = numeros <= 6
    te = (numeros >= 7) & (numeros <= 12)
    modelo = entrenar(a.modelo, X[tr], y[tr])
    prob = modelo.predict(X[te], verbose=0)
    informe(y[te], prob.argmax(1), "[1] MISMO GRUPO, reps 7-12 (OPTIMISTA)")
    print(f"  top-3: {top_k(prob, y[te]):.1%}")

    # 2) Dejando una persona fuera (métrica real)
    todo_real, todo_pred, todo_prob = [], [], []
    for fuera in sorted(set(personas)):
        modelo = entrenar(a.modelo, X[personas != fuera], y[personas != fuera])
        prob = modelo.predict(X[personas == fuera], verbose=0)
        real = y[personas == fuera]
        print(f"\n  fuera = {fuera}: top-1 {np.mean(prob.argmax(1) == real):.1%} | top-3 {top_k(prob, real):.1%}")
        todo_real.append(real); todo_pred.append(prob.argmax(1)); todo_prob.append(prob)
    real, pred = np.concatenate(todo_real), np.concatenate(todo_pred)
    informe(real, pred, "[2] DEJANDO UNA PERSONA FUERA (métrica real)")
    print(f"  top-3: {top_k(np.concatenate(todo_prob), real):.1%}  (azar top-1: {1/len(CLASES):.1%})")

    if a.guardar:
        modelo = entrenar(a.modelo, X, y)
        ruta = SALIDA / "lsm_tramites.h5"
        modelo.save(ruta)
        (SALIDA / "clases_tramites.json").write_text(json.dumps(CLASES, ensure_ascii=False))
        print(f"\nModelo guardado en {ruta} y clases en clases_tramites.json")


if __name__ == "__main__":
    main()