"""
preprocesar.py
Preparación de secuencias (30, 226) para LSM-Connect.
Se usa IGUAL en entrenamiento y en la cámara en vivo (si no, el modelo falla).

Layout del frame (226): mano der 0:63 | mano izq 63:126 | pose 126:226 (25 puntos x,y,z,vis)

normalizar_secuencia():
  1. Centra todo en el centro de los hombros y divide entre el ancho de hombros
     (quita diferencias de distancia/posición de la persona respecto a la cámara).
  2. Reubica el resultado en un marco de referencia fijo (centro y ancho canónicos),
     para que los valores queden en un rango parecido al que vio el modelo base.
  3. Apaga la mano que está en reposo (muñeca muy por debajo de los hombros):
     Alejandro la tenía visible y Mauro no, y el modelo aprendía eso en vez de la seña.
aumentar_secuencia(): aumento de datos SOLO para entrenar.
"""
import numpy as np

N_FRAMES, N_FEATS = 30, 226
HOMBRO_IZQ, HOMBRO_DER = 11, 12
REF_CENTRO = np.array([0.5, 0.40], dtype=np.float32)  # marco canónico (x, y)
REF_ANCHO = 0.25
UMBRAL_REPOSO = 1.0  # anchos de hombro por debajo de los hombros -> mano en reposo


def _partes(seq: np.ndarray):
    mano_d = seq[:, 0:63].reshape(-1, 21, 3).copy()
    mano_i = seq[:, 63:126].reshape(-1, 21, 3).copy()
    pose = seq[:, 126:226].reshape(-1, 25, 4).copy()
    return mano_d, mano_i, pose


def normalizar_secuencia(seq: np.ndarray, apagar_reposo: bool = True) -> np.ndarray:
    """(30,226) crudo -> (30,226) normalizado, mismo layout."""
    seq = np.asarray(seq, dtype=np.float32)
    if seq.shape != (N_FRAMES, N_FEATS):
        raise ValueError(f"Shape inesperado: {seq.shape}")
    mano_d, mano_i, pose = _partes(seq)

    centro = (pose[:, HOMBRO_IZQ, :2] + pose[:, HOMBRO_DER, :2]) / 2
    ancho = np.linalg.norm(pose[:, HOMBRO_IZQ, :2] - pose[:, HOMBRO_DER, :2], axis=-1)
    # Un solo centro/ancho por secuencia (mediana): evita saltos si un frame falla
    ok = ancho > 1e-3
    if not ok.any():
        return np.zeros_like(seq)
    c = np.median(centro[ok], axis=0)
    w = float(np.median(ancho[ok]))

    def mover(pts):
        pts[..., :2] = (pts[..., :2] - c) / w * REF_ANCHO + REF_CENTRO
        pts[..., 2] = pts[..., 2] / w * REF_ANCHO
        return pts

    salidas = []
    for mano in (mano_d, mano_i):
        falta = np.abs(mano).sum(axis=(1, 2)) == 0
        y_rel = (mano[:, 0, 1] - c[1]) / w          # altura de la muñeca vs hombros
        if apagar_reposo:
            falta = falta | (y_rel > UMBRAL_REPOSO)
        mano = mover(mano)
        mano[falta] = 0
        salidas.append(mano.reshape(-1, 63))
    pose = mover_pose(pose, c, w)
    return np.concatenate(salidas + [pose.reshape(-1, 100)], axis=1).astype(np.float32)


def mover_pose(pose: np.ndarray, c: np.ndarray, w: float) -> np.ndarray:
    pose[..., :2] = (pose[..., :2] - c) / w * REF_ANCHO + REF_CENTRO
    pose[..., 2] = pose[..., 2] / w * REF_ANCHO
    return pose  # la visibilidad (col 3) no se toca


def aumentar_secuencia(seq: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Aumento sobre una secuencia YA normalizada. Mantiene los ceros (mano ausente)."""
    seq = seq.copy()
    ausente = np.stack([np.abs(seq[:, 0:63]).sum(1) == 0, np.abs(seq[:, 63:126]).sum(1) == 0], 1)
    # --- velocidad: remuestrea en el tiempo (0.85x a 1.15x) ---
    factor = rng.uniform(0.85, 1.15)
    t_src = np.clip(np.arange(N_FRAMES) * factor + rng.uniform(-1.5, 1.5), 0, N_FRAMES - 1)
    idx = np.rint(t_src).astype(int)
    seq, ausente = seq[idx], ausente[idx]
    # --- geometría: escala, giro y desplazamiento alrededor del centro de referencia ---
    escala = rng.uniform(0.9, 1.1)
    ang = np.deg2rad(rng.uniform(-8, 8))
    desp = rng.uniform(-0.03, 0.03, size=2)
    rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]], dtype=np.float32)

    def tf_xy(xy):
        return ((xy - REF_CENTRO) * escala) @ rot.T + REF_CENTRO + desp

    for ini, n in ((0, 21), (63, 21), (126, 25)):
        paso = 3 if ini < 126 else 4
        bloque = seq[:, ini:ini + n * paso].reshape(N_FRAMES, n, paso)
        bloque[..., :2] = tf_xy(bloque[..., :2])
        bloque[..., 2] *= escala
        seq[:, ini:ini + n * paso] = bloque.reshape(N_FRAMES, -1)
    # --- ruido y pérdida aleatoria de detección de mano ---
    seq[:, :126] += rng.normal(0, 0.004, size=seq[:, :126].shape).astype(np.float32)
    perdida = rng.random((N_FRAMES, 2)) < 0.05
    for j, ini in enumerate((0, 63)):
        quitar = ausente[:, j] | perdida[:, j]
        seq[quitar, ini:ini + 63] = 0
    return seq.astype(np.float32)