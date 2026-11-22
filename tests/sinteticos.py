"""
Datos sintéticos para probar el flujo completo sin cámara ni personas: una "persona" de puntos
con hombros fijos y una mano que sube, hace una forma (letra) o un recorrido (seña) y baja.
No sirven para entrenar el sistema real, solo para verificar que el código funciona.
"""
from __future__ import annotations

import json

import numpy as np

from lsm import puntos as P
from lsm.datos import carpeta_sesion, nombre_clip
from lsm.config import DIR_PUNTOS, DIR_VIDEOS

HOMBRO_I, HOMBRO_D = np.array([0.60, 0.30]), np.array([0.40, 0.30])  # izq de la persona = derecha de la imagen
REPOSO_D, REPOSO_I = np.array([0.42, 0.62]), np.array([0.58, 0.62])  # manos colgando
ARRIBA_D = np.array([0.38, 0.22])                                    # mano derecha levantada


def plantilla(semilla: int) -> np.ndarray:
    """Forma de mano (21, 3) distinta por letra, relativa a la muñeca."""
    rng = np.random.default_rng(semilla)
    base = np.zeros((21, 3), np.float32)
    base[1:, :2] = rng.uniform(-1, 1, (20, 2))
    base[9, :2] = [0.0, -1.0]                    # nudillo medio fijo: la palma mide 1
    base[5, :2], base[17, :2] = [-0.4, -0.9], [0.4, -0.9]
    base[:, 2] = rng.normal(0, 0.1, 21)
    return base


def _pose(rng) -> np.ndarray:
    pose = np.zeros((33, 4), np.float32)
    pose[:, 3] = 1.0
    pose[0, :2] = [0.5, 0.15]
    pose[11, :2], pose[12, :2] = HOMBRO_I, HOMBRO_D
    pose[13, :2], pose[14, :2] = [0.65, 0.45], [0.35, 0.45]
    pose[23, :2], pose[24, :2] = [0.56, 0.7], [0.44, 0.7]
    pose[:, :2] += rng.normal(0, 0.002, (33, 2))
    return pose


def _mano(muneca, forma, rng, escala=0.05) -> np.ndarray:
    m = np.zeros((21, 3), np.float32)
    m[:, :2] = muneca + forma[:, :2] * escala
    m[:, 2] = forma[:, 2] * escala
    return m + rng.normal(0, 0.0015, m.shape).astype(np.float32)


def clip_desde_guion(guion, fps=30, zurdo=False, semilla=0) -> dict:
    """guion: lista de (segundos, muneca_fn(t_rel) -> xy | None, forma (21,3) | None).
    None en la muñeca = mano en reposo."""
    rng = np.random.default_rng(semilla)
    reposo_forma = plantilla(999)
    cuadros, tiempos, t = [], [], 0.0
    for dur, muneca_fn, forma in guion:
        for k in range(max(1, int(round(dur * fps)))):
            c = P.vacio()
            c["pose"] = _pose(rng)
            rel = k / max(1, dur * fps)
            if muneca_fn is None:
                c["mano_der"] = _mano(REPOSO_D, reposo_forma, rng)
            else:
                c["mano_der"] = _mano(np.asarray(muneca_fn(rel)), forma, rng)
            c["mano_izq"] = _mano(REPOSO_I, reposo_forma, rng) if rng.random() < 0.5 else np.zeros((21, 3), np.float32)
            cuadros.append(c)
            tiempos.append(t)
            t += 1 / fps
    clip = P.apilar(cuadros, tiempos)
    if zurdo:
        from lsm.rasgos import espejar

        clip = espejar(clip)
    return clip


def _subir(rel):
    return REPOSO_D + (ARRIBA_D - REPOSO_D) * rel


def _bajar(rel):
    return ARRIBA_D + (REPOSO_D - ARRIBA_D) * rel


def clip_letra(semilla_letra: int, movimiento=False, **kw) -> dict:
    forma = plantilla(semilla_letra)
    if movimiento:
        def muneca(rel):
            return ARRIBA_D + 0.04 * np.array([np.cos(rel * 6 * np.pi), np.sin(rel * 6 * np.pi)])
    else:
        def muneca(rel):
            return ARRIBA_D
    return clip_desde_guion([(0.6, None, None), (0.2, _subir, forma), (1.6, muneca, forma),
                             (0.2, _bajar, forma), (0.8, None, None)], **kw)


def clip_deletreo(semillas: list[int], movimientos: list[bool], **kw) -> dict:
    guion = [(0.6, None, None), (0.2, _subir, plantilla(semillas[0]))]
    for s, mov in zip(semillas, movimientos):
        forma = plantilla(s)
        if mov:
            guion.append((0.6, lambda rel: ARRIBA_D + 0.04 * np.array(
                [np.cos(rel * 4 * np.pi), np.sin(rel * 4 * np.pi)]), forma))
        else:
            guion.append((0.5, lambda rel: ARRIBA_D, forma))
        guion.append((0.08, lambda rel: ARRIBA_D, plantilla(12345)))  # transición
    guion += [(0.2, _bajar, plantilla(semillas[-1])), (0.8, None, None)]
    return clip_desde_guion(guion, **kw)


RECORRIDOS = [
    lambda rel: ARRIBA_D + np.array([0.15 * rel, 0.0]),                       # a la derecha
    lambda rel: ARRIBA_D + np.array([0.0, -0.1 * rel]),                       # hacia arriba
    lambda rel: ARRIBA_D + 0.06 * np.array([np.cos(rel * 4 * np.pi), np.sin(rel * 4 * np.pi)]),  # círculos
    lambda rel: ARRIBA_D + np.array([0.12 * rel, 0.06 * np.sin(rel * 6 * np.pi)]),  # zigzag
]


def clip_sena(k: int, **kw) -> dict:
    forma = plantilla(500 + k)
    return clip_desde_guion([(0.6, None, None), (0.25, _subir, forma), (1.2, RECORRIDOS[k], forma),
                             (0.25, _bajar, forma), (0.8, None, None)], **kw)


def clip_negativo(**kw) -> dict:
    forma = plantilla(777)
    # se rasca la cabeza: la mano sube cerca de la cara, se queda quieta y baja
    return clip_desde_guion([(0.5, None, None), (0.3, _subir, forma),
                             (1.0, lambda rel: np.array([0.45, 0.12]) + 0.01 * np.sin(rel * 20), forma),
                             (0.3, _bajar, forma), (0.6, None, None)], **kw)


def guardar_clip(clip: dict, persona: str, sesion: str, tipo: str, etiqueta: str, rep: int,
                 texto: str = "", modo=None) -> None:
    nombre = nombre_clip(tipo, etiqueta, rep)
    cv = carpeta_sesion(persona, sesion, DIR_VIDEOS)
    cp = carpeta_sesion(persona, sesion, DIR_PUNTOS)
    cv.mkdir(parents=True, exist_ok=True)
    cp.mkdir(parents=True, exist_ok=True)
    meta = dict(persona=persona, sesion=sesion, tipo=tipo, etiqueta=etiqueta, texto=texto or etiqueta,
                repeticion=rep, modo=modo, tiempos=clip["t"].tolist(), calidad={"avisos": []})
    (cv / f"{nombre}.json").write_text(json.dumps(meta), encoding="utf-8")
    P.guardar(cp / f"{nombre}.npz", clip)
