"""
Utilidades de entrenamiento compartidas por herramientas/entrenar_letras.py y entrenar_senas.py.

Reglas que evitan los errores del prototipo anterior:
  - Se evalúa SIEMPRE dejando personas fuera (la persona de prueba nunca se vio al entrenar).
  - La validación para detener el entrenamiento se separa ANTES del aumento de datos y por
    persona (antes, copias aumentadas de la misma grabación caían en entrenamiento y validación).
  - Las personas de protocolo/particion.json no se usan para nada salvo la prueba final.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Callable

import numpy as np

from . import puntos as P
from .rasgos import VENTANA_N, N_RASGOS_LETRA, secuencia_sena, ventanas_letra_clip
from .segmentador import activos_por_cuadro, segmentar_clip, segmento_principal
from .vocabulario import NADA

SEMILLA = 42


def fijar_semillas(semilla: int = SEMILLA) -> None:
    import tensorflow as tf

    random.seed(semilla)
    np.random.seed(semilla)
    tf.random.set_seed(semilla)


# ====================================================================== ejemplos
def ejemplos_letras(clips, paso: int = 2):
    """-> X (N, 8, 66), y (N,) etiquetas, grupos (N,) persona. Toma las ventanas que el servidor
    vería en la parte central (estable) de cada letra; los 'negativos' dan la clase _nada."""
    X, y, g, omitidos = [], [], [], []
    for clip in clips:
        datos = P.cargar(clip.puntos)
        if len(datos["t"]) < 5:
            continue
        ventanas = ventanas_letra_clip(datos)
        activos = activos_por_cuadro(datos)
        if clip.tipo == "negativo":
            idx = np.flatnonzero(activos)[::paso]
            etiqueta = NADA
        else:
            ev = segmento_principal(datos, 20.0)
            act = np.flatnonzero(activos[ev.ini:ev.fin]) + ev.ini if ev else np.zeros(0, int)
            if len(act) < 4:
                omitidos.append(clip.json.stem)
                continue
            a0, a1 = act[0], act[-1]
            largo = a1 - a0 + 1
            central = np.arange(a0 + int(0.2 * largo), a1 + 1 - int(0.15 * largo))
            idx = central[activos[central]][::paso]
            etiqueta = clip.etiqueta
        for i in idx:
            X.append(ventanas[i])
            y.append(etiqueta)
            g.append(clip.persona)
    if omitidos:
        print(f"  Aviso: {len(omitidos)} clips sin mano levantada se omitieron (p. ej. {omitidos[:3]})")
    X = np.array(X, np.float32).reshape(-1, VENTANA_N, N_RASGOS_LETRA)
    return X, np.array(y), np.array(g)


def ejemplos_senas(clips):
    """-> X (N, 90, F), y (N,), grupos (N,). Cada seña se corta con el segmentador (igual que
    en vivo). Los segmentos de los clips 'negativo' dan la clase _nada."""
    X, y, g, omitidos = [], [], [], []
    for clip in clips:
        datos = P.cargar(clip.puntos)
        if len(datos["t"]) < 5:
            continue
        if clip.tipo == "negativo":
            for ev in segmentar_clip(datos):
                X.append(secuencia_sena(ev.clip())[0])
                y.append(NADA)
                g.append(clip.persona)
            continue
        ev = segmento_principal(datos)
        if ev is None:
            omitidos.append(clip.json.stem)
            continue
        X.append(secuencia_sena(ev.clip())[0])
        y.append(clip.etiqueta)
        g.append(clip.persona)
    if omitidos:
        print(f"  Aviso: {len(omitidos)} clips sin seña detectada se omitieron (p. ej. {omitidos[:3]})")
    return np.array(X, np.float32), np.array(y), np.array(g)


# ====================================================================== aumento de datos
def _rotar_xy(xy: np.ndarray, ang: float) -> np.ndarray:
    c, s = np.cos(ang), np.sin(ang)
    return xy @ np.array([[c, -s], [s, c]], np.float32).T


def _aumentar_mano(m: np.ndarray, rng) -> np.ndarray:
    """m (..., 66): rasgos de una mano. Gira la forma, mueve la posición y agrega ruido."""
    m = m.copy()
    esta = m[..., 65:66] > 0
    forma = m[..., :63].reshape(*m.shape[:-1], 21, 3)
    forma[..., :2] = _rotar_xy(forma[..., :2], rng.uniform(-0.25, 0.25)) * rng.uniform(0.93, 1.07)
    forma += rng.normal(0, 0.03, forma.shape).astype(np.float32)
    m[..., :63] = forma.reshape(*m.shape[:-1], 63)
    m[..., 63:65] += rng.uniform(-0.15, 0.15, 2).astype(np.float32)
    return np.where(esta, m, 0.0)


def aumentar_letra(x: np.ndarray, rng) -> np.ndarray:
    return _aumentar_mano(x, rng)


def aumentar_sena(x: np.ndarray, rng) -> np.ndarray:
    """x (90, F) con relleno. Cambia velocidad, gira/escala el cuerpo y las manos, agrega ruido."""
    validos = int((np.abs(x).sum(1) > 0).sum())
    if validos < 2:
        return x
    n = int(np.clip(round(validos * rng.uniform(0.8, 1.2)), 2, len(x)))
    idx = np.clip(np.round(np.linspace(0, validos - 1, n) + rng.uniform(-0.5, 0.5, n)), 0, validos - 1).astype(int)
    v = x[idx].copy()
    ang, esc = rng.uniform(-0.14, 0.14), rng.uniform(0.9, 1.1)
    desp = rng.uniform(-0.1, 0.1, 2).astype(np.float32)
    for ini in (0, 66):
        mano = v[:, ini:ini + 66]
        esta = mano[:, 65:66] > 0
        mano = _aumentar_mano(mano, rng)
        mano[:, 63:65] = _rotar_xy(mano[:, 63:65], ang) * esc + desp
        v[:, ini:ini + 66] = np.where(esta, mano, 0.0)
    cuerpo = v[:, 132:].reshape(len(v), -1, 2)
    ok = np.abs(cuerpo).sum(-1, keepdims=True) > 0
    cuerpo = np.where(ok, _rotar_xy(cuerpo, ang) * esc + desp + rng.normal(0, 0.01, cuerpo.shape), 0.0)
    v[:, 132:] = cuerpo.reshape(len(v), -1)
    salida = np.zeros_like(x)
    salida[:len(v)] = v
    return salida


def aumentar(X, y, fn: Callable, copias: int, rng):
    if copias <= 0:
        return X, y
    extra = [fn(x, rng) for x in X for _ in range(copias)]
    return np.concatenate([X, np.array(extra, np.float32)]), np.concatenate([y, np.repeat(y, copias)])


# ====================================================================== entrenamiento
def pesos_clase(y: np.ndarray, n_clases: int) -> dict:
    cuenta = np.bincount(y, minlength=n_clases).astype(float)
    cuenta[cuenta == 0] = 1
    pesos = len(y) / (n_clases * cuenta)
    return {i: float(p) for i, p in enumerate(pesos)}


def entrenar(X, y, grupos, n_clases: int, construir: Callable, aumentar_fn: Callable,
             copias: int, epocas: int, lote: int = 64, verbose: int = 0):
    """Entrena con validación por persona (si hay ≥3) separada ANTES de aumentar."""
    import tf_keras as keras

    fijar_semillas()
    rng = np.random.default_rng(SEMILLA)
    personas = sorted(set(grupos))
    if len(personas) >= 3:
        val_persona = personas[rng.integers(len(personas))]
        val = grupos == val_persona
    else:  # muy pocas personas: 15 % al azar (solo para pruebas con pocos datos)
        val = rng.random(len(y)) < 0.15
    Xtr, ytr = aumentar(X[~val], y[~val], aumentar_fn, copias, rng)
    orden = rng.permutation(len(ytr))
    keras.backend.clear_session()
    modelo = construir(X.shape[1:], n_clases)
    datos_val = (X[val], y[val]) if val.any() else None
    cb = [keras.callbacks.EarlyStopping(monitor="val_loss" if datos_val else "loss", patience=8,
                                        restore_best_weights=True)]
    modelo.fit(Xtr[orden], ytr[orden], validation_data=datos_val, epochs=epocas, batch_size=lote,
               class_weight=pesos_clase(ytr, n_clases), callbacks=cb, verbose=verbose)
    return modelo


def pliegues_por_persona(grupos, max_pliegues: int = 5) -> list[list[str]]:
    personas = sorted(set(grupos))
    if len(personas) <= max_pliegues:
        return [[p] for p in personas]
    pliegues = [[] for _ in range(max_pliegues)]
    for i, p in enumerate(personas):
        pliegues[i % max_pliegues].append(p)
    return pliegues


def predecir(modelo, X, lote: int = 256) -> np.ndarray:
    return modelo.predict(X, batch_size=lote, verbose=0)


def informe(y_real: np.ndarray, prob: np.ndarray, clases: list[str], grupos=None, titulo: str = "") -> dict:
    pred = prob.argmax(1)
    top3 = np.mean([y_real[i] in np.argsort(-prob[i])[:3] for i in range(len(y_real))]) if len(y_real) else 0
    acc = float(np.mean(pred == y_real)) if len(y_real) else 0.0
    print(f"\n{titulo}\n  Precisión: {acc:.1%}  | correcta entre las 3 primeras: {top3:.1%} "
          f"| muestras: {len(y_real)} | azar: {1 / max(len(clases), 1):.1%}")
    if grupos is not None:
        por_p = defaultdict(list)
        for yr, yp, gp in zip(y_real, pred, grupos):
            por_p[gp].append(yr == yp)
        print("  Por persona: " + ", ".join(f"{p} {np.mean(v):.0%}" for p, v in sorted(por_p.items())))
    por_clase = sorted((float(np.mean(pred[y_real == i] == i)), c, int((y_real == i).sum()))
                       for i, c in enumerate(clases) if (y_real == i).any())
    print("  Las 8 clases más difíciles: " + ", ".join(f"{c} {a:.0%}" for a, c, _ in por_clase[:8]))
    conf = Counter((clases[a], clases[b]) for a, b in zip(y_real, pred) if a != b)
    if conf:
        print("  Confusiones más frecuentes: " + ", ".join(f"{a}->{b} ({n})" for (a, b), n in conf.most_common(8)))
    return dict(precision=round(acc, 4), top3=round(float(top3), 4), muestras=int(len(y_real)))


def validacion_cruzada(X, y, grupos, clases, construir, aumentar_fn, copias, epocas, titulo):
    """Cada pliegue deja fuera a una o más personas completas. Es la métrica que importa."""
    pliegues = pliegues_por_persona(grupos)
    if len(pliegues) < 2:
        print("\n(Validación por persona omitida: se necesitan al menos 2 personas.)")
        return None
    reales, probs, gs = [], [], []
    for fuera in pliegues:
        te = np.isin(grupos, fuera)
        modelo = entrenar(X[~te], y[~te], grupos[~te], len(clases), construir, aumentar_fn, copias, epocas)
        probs.append(predecir(modelo, X[te]))
        reales.append(y[te])
        gs.append(grupos[te])
        print(f"  fuera {','.join(fuera)}: {np.mean(probs[-1].argmax(1) == y[te]):.1%}")
    return informe(np.concatenate(reales), np.concatenate(probs), clases, np.concatenate(gs), titulo)
