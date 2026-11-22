"""
Rasgos (features) que entran a los modelos. Se calculan IGUAL al entrenar y en vivo.

Dos familias:
  - Letras (deletreo): solo la mano que está deletreando. Forma de la mano centrada en la muñeca
    y escalada por el tamaño de la palma (no importa la distancia a la cámara ni el tamaño de la
    mano) + posición de la muñeca respecto a los hombros. Se arma una VENTANA de los últimos
    0.6 s, para que las letras con movimiento (J, Z, Ñ...) también se distingan.
  - Señas (palabra completa): ambas manos (forma + posición) + parte superior del cuerpo,
    normalizado por el centro y el ancho de los hombros, remuestreado a 15 cuadros/s.

Zurdos: todo se pasa a "mano dominante = derecha" con un espejo (espejar), así una persona
zurda se ve igual que una diestra y el modelo no necesita aprender las dos versiones.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from . import puntos as P

HOMBRO_IZQ, HOMBRO_DER = 11, 12
POSE_SUP = list(range(23))      # cabeza, hombros, brazos y manos del cuerpo (sin cadera ni piernas)
PARES_POSE = [(1, 4), (2, 5), (3, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16), (17, 18),
              (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)]
UMBRAL_REPOSO = 1.0             # muñeca más de 1 ancho de hombros por debajo de ellos = mano en reposo
MIN_VISIBILIDAD = 0.5

N_RASGOS_MANO = 63 + 3          # forma (21x3) + posición de la muñeca (x, y) + presente
N_RASGOS_LETRA = N_RASGOS_MANO
N_RASGOS_SENA = 2 * N_RASGOS_MANO + 2 * len(POSE_SUP)

VENTANA_S, VENTANA_N = 0.6, 8   # letras: últimos 0.6 s muestreados en 8 puntos
FPS_SENA, MAX_CUADROS_SENA = 15, 90  # señas: 15 cuadros/s, máximo 6 s (si dura más se comprime)


# ------------------------------------------------------------------ utilidades geométricas
def presente(arr: np.ndarray) -> np.ndarray:
    """(…, N, D) -> (…) True si ese conjunto de puntos fue detectado."""
    return np.abs(arr).sum(axis=(-1, -2)) > 0


def _hombros_validos(pose: np.ndarray) -> np.ndarray:
    h = pose[..., [HOMBRO_IZQ, HOMBRO_DER], :]
    return (np.abs(h[..., :2]).sum(axis=(-1, -2)) > 0) & (h[..., 3].min(axis=-1) >= MIN_VISIBILIDAD)


def referencia(pose: np.ndarray):
    """pose (T, 33, 4) -> (centro (2,), ancho) con la mediana de los cuadros válidos, o None."""
    ok = _hombros_validos(pose)
    if not ok.any():
        return None
    izq, der = pose[ok, HOMBRO_IZQ, :2], pose[ok, HOMBRO_DER, :2]
    ancho = float(np.median(np.linalg.norm(izq - der, axis=-1)))
    if ancho < 1e-3:
        return None
    return np.median((izq + der) / 2, axis=0).astype(np.float32), ancho


class ReferenciaHombros:
    """Referencia en flujo (cuadro a cuadro): mediana de los últimos n cuadros con hombros."""

    def __init__(self, n: int = 15) -> None:
        self._hist: deque = deque(maxlen=n)

    def empujar(self, pose: np.ndarray):
        if _hombros_validos(pose):
            self._hist.append(pose)
        return referencia(np.stack(self._hist)) if self._hist else None


def mano_activa(mano: np.ndarray, ref) -> np.ndarray:
    """mano (…, 21, 3) -> (…) True si la mano está detectada y levantada (no colgando en reposo)."""
    esta = presente(mano)
    if ref is None:
        return esta
    centro, ancho = ref
    return esta & ((mano[..., 0, 1] - centro[1]) / ancho <= UMBRAL_REPOSO)


# ------------------------------------------------------------------ espejo / mano dominante
def espejar(clip: dict) -> dict:
    """Voltea izquierda-derecha: x -> 1 - x, intercambia manos y lados del cuerpo."""
    out = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in clip.items()}
    for k in P.PARTES:
        arr = out[k]
        ok = np.abs(arr).sum(axis=-1) > 0          # no tocar los ceros (punto no detectado)
        arr[..., 0] = np.where(ok, 1.0 - arr[..., 0], 0.0)
    out["mano_der"], out["mano_izq"] = out["mano_izq"], out["mano_der"]
    pose = out["pose"]
    for a, b in PARES_POSE:
        pose[..., [a, b], :] = pose[..., [b, a], :]
    return out


def mano_dominante(clip: dict, ref=None) -> str:
    """'der' o 'izq': la mano que pasa más tiempo levantada en el clip."""
    ref = ref if ref is not None else referencia(clip["pose"])
    der = mano_activa(clip["mano_der"], ref).sum()
    izq = mano_activa(clip["mano_izq"], ref).sum()
    return "izq" if izq > der else "der"


def canonizar(clip: dict, ref=None) -> tuple[dict, bool]:
    """Deja la mano dominante como 'mano_der'. Devuelve (clip, se_espejo)."""
    if mano_dominante(clip, ref) == "izq":
        return espejar(clip), True
    return clip, False


# ------------------------------------------------------------------ rasgos de una mano
def rasgos_mano(mano: np.ndarray, ref) -> np.ndarray:
    """mano (…, 21, 3) -> (…, 66): forma normalizada (63) + muñeca vs hombros (2) + presente (1)."""
    mano = np.asarray(mano, np.float32)
    esta = presente(mano)
    rel = mano - mano[..., :1, :]
    palma = (np.linalg.norm(rel[..., 9, :2], axis=-1) + np.linalg.norm(
        mano[..., 5, :2] - mano[..., 17, :2], axis=-1)) / 2
    forma = rel / np.maximum(palma, 1e-4)[..., None, None]
    forma = forma.reshape(*mano.shape[:-2], 63)
    if ref is None:
        pos = np.zeros((*mano.shape[:-2], 2), np.float32)
    else:
        centro, ancho = ref
        pos = (mano[..., 0, :2] - centro) / ancho
    salida = np.concatenate([forma, pos, np.ones((*mano.shape[:-2], 1), np.float32)], axis=-1)
    return np.where(esta[..., None], salida, 0.0).astype(np.float32)


def rasgos_letra(cuadro_canonico: dict, ref) -> np.ndarray:
    """Un cuadro (mano dominante ya como 'mano_der') -> (66,)."""
    return rasgos_mano(cuadro_canonico["mano_der"], ref)


class VentanaLetras:
    """Acumula rasgos por cuadro y arma la ventana (VENTANA_N, 66) de los últimos VENTANA_S s.
    Se muestrea por TIEMPO (no por número de cuadros): funciona igual a 12 fps en vivo que a
    30 fps en los videos de la captura."""

    def __init__(self) -> None:
        self._t: deque = deque()
        self._x: deque = deque()

    def reiniciar(self) -> None:
        self._t.clear()
        self._x.clear()

    def empujar(self, t: float, rasgos: np.ndarray) -> np.ndarray:
        self._t.append(t)
        self._x.append(rasgos)
        while self._t and t - self._t[0] > VENTANA_S + 0.3:
            self._t.popleft()
            self._x.popleft()
        tiempos = np.asarray(self._t)
        objetivo = np.linspace(t - VENTANA_S, t, VENTANA_N)
        idx = np.clip(np.searchsorted(tiempos, objetivo, side="right") - 1, 0, len(tiempos) - 1)
        return np.stack([self._x[i] for i in idx])


# ------------------------------------------------------------------ rasgos de una seña
def rasgos_sena_cuadros(clip_canonico: dict, ref) -> np.ndarray:
    """clip (T, …) con la dominante como 'mano_der' -> (T, N_RASGOS_SENA)."""
    der = rasgos_mano(clip_canonico["mano_der"], ref)
    izq = rasgos_mano(clip_canonico["mano_izq"], ref)
    pose = clip_canonico["pose"][:, POSE_SUP]
    if ref is None:
        cuerpo = np.zeros((len(pose), 2 * len(POSE_SUP)), np.float32)
    else:
        centro, ancho = ref
        cuerpo = (pose[..., :2] - centro) / ancho
        cuerpo = np.where((pose[..., 3] >= MIN_VISIBILIDAD)[..., None], cuerpo, 0.0)
        cuerpo = cuerpo.reshape(len(pose), -1)
    return np.concatenate([der, izq, cuerpo], axis=1).astype(np.float32)


def indices_remuestreo(t: np.ndarray) -> np.ndarray:
    """Índices (vecino más cercano) para pasar el segmento a FPS_SENA, máximo MAX_CUADROS_SENA."""
    t = np.asarray(t, np.float64)
    if len(t) == 0:
        return np.zeros(0, int)
    n = int(np.floor((t[-1] - t[0]) * FPS_SENA)) + 1
    n = max(1, min(n, MAX_CUADROS_SENA))
    objetivo = np.linspace(t[0], t[-1], n)
    return np.abs(t[None, :] - objetivo[:, None]).argmin(axis=1)


def secuencia_sena(segmento: dict) -> tuple[np.ndarray, bool]:
    """Segmento (clip con 't') -> ((MAX_CUADROS_SENA, N_RASGOS_SENA) con relleno de ceros, se_espejo).
    La referencia de hombros es la mediana del segmento."""
    ref = referencia(segmento["pose"])
    canon, espejo = canonizar(segmento, ref)
    x = rasgos_sena_cuadros(canon, ref)[indices_remuestreo(segmento["t"])]
    salida = np.zeros((MAX_CUADROS_SENA, N_RASGOS_SENA), np.float32)
    salida[:len(x)] = x
    return salida, espejo


# ------------------------------------------------------------------ deletreo: qué mano usar
class SelectorMano:
    """Para el deletreo, cuadro a cuadro: usa la mano que está levantada. Si están las dos (o
    ninguna), conserva la última elegida. Lo usan igual el entrenamiento y el servidor."""

    def __init__(self) -> None:
        self.lado = "der"

    def reiniciar(self) -> None:
        self.lado = "der"

    def elegir(self, cuadro: dict, ref) -> str:
        der = bool(mano_activa(cuadro["mano_der"], ref))
        izq = bool(mano_activa(cuadro["mano_izq"], ref))
        if der != izq:
            self.lado = "der" if der else "izq"
        return self.lado

    def canonico(self, cuadro: dict, ref) -> dict:
        return espejar(cuadro) if self.elegir(cuadro, ref) == "izq" else cuadro


def ventanas_letra_clip(clip: dict) -> np.ndarray:
    """Clip completo -> (T, VENTANA_N, 66): la ventana que el servidor vería en cada cuadro."""
    ref_h, selector, ventana = ReferenciaHombros(), SelectorMano(), VentanaLetras()
    salida = np.zeros((len(clip["t"]), VENTANA_N, N_RASGOS_LETRA), np.float32)
    for i, t in enumerate(clip["t"]):
        c = P.cuadro(clip, i)
        ref = ref_h.empujar(c["pose"])
        salida[i] = ventana.empujar(float(t), rasgos_letra(selector.canonico(c, ref), ref))
    return salida
