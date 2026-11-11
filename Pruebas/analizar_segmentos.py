"""
analizar_segmentos.py
Compara los segmentos capturados en vivo (Pruebas/debug_segmentos/, se generan con
iniciar_demo.bat debug  o  python Modelo_ia/probar_motor_camara.py) contra el dataset.

Para cada segmento muestra: frames, % con mano der/izq, % en posición de firmar,
dónde empieza/termina la seña, qué predice el modelo y a qué grabación del dataset
se parece más (vecino más cercano). Al final, los mismos números promedio del dataset.

Uso (raíz del repo, venv activo):
    python Pruebas/analizar_segmentos.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "Modelo_ia"))
sys.path.insert(0, str(RAIZ / "Backend"))

from captura_dataset_tramites import remuestrear  # noqa: E402
from preprocesar import normalizar_secuencia  # noqa: E402
from app.motores import MotorReal  # noqa: E402

DEBUG_DIR = RAIZ / "Pruebas" / "debug_segmentos"
DATASET = RAIZ / "dataset_tramites"


class _Regla:  # para reusar MotorReal._activa sin cargar MediaPipe
    from preprocesar import UMBRAL_REPOSO as _umbral_reposo


def stats(seq: np.ndarray) -> dict:
    act = np.array([MotorReal._activa(_Regla, v) for v in seq])
    n = len(seq)
    return {
        "frames": n,
        "mano_der": float(np.mean([v[0:63].any() for v in seq])),
        "mano_izq": float(np.mean([v[63:126].any() for v in seq])),
        "hombros": float(np.mean([v[126:].reshape(25, 4)[[11, 12], :2].any() for v in seq])),
        "activa": float(act.mean()),
        "inicio": float(np.argmax(act) / n) if act.any() else -1,
        "fin": float((n - 1 - np.argmax(act[::-1])) / n) if act.any() else -1,
    }


def main() -> None:
    import tf_keras as keras

    modelo = keras.models.load_model(RAIZ / "Modelo_ia" / "lsm_tramites.h5")
    clases = json.loads((RAIZ / "Modelo_ia" / "clases_tramites.json").read_text(encoding="utf-8"))

    ref_X, ref_lbl, ref_stats = [], [], []
    for c in clases:
        for f in sorted((DATASET / c).glob("*.npy")):
            s = np.load(f)
            ref_X.append(normalizar_secuencia(s).ravel())
            ref_lbl.append(f"{c}/{f.stem}")
            ref_stats.append(stats(s))
    ref_X = np.array(ref_X)

    archivos = sorted(DEBUG_DIR.glob("*.npy"))
    if not archivos:
        sys.exit(f"No hay segmentos en {DEBUG_DIR}. Corre primero: iniciar_demo.bat debug")

    print(f"{'archivo':34s} {'fr':>3s} {'der':>4s} {'izq':>4s} {'homb':>4s} {'act':>4s} "
          f"{'ini':>4s} {'fin':>4s}  predicción               | más parecido en dataset")
    for f in archivos:
        crudo = np.load(f)
        st = stats(crudo)
        seq = normalizar_secuencia(remuestrear(list(crudo)))
        prob = modelo.predict(seq[None], verbose=0)[0]
        top = ", ".join(f"{clases[i]} {prob[i]:.0%}" for i in np.argsort(-prob)[:2])
        vecino = ref_lbl[int(np.argmin(np.linalg.norm(ref_X - seq.ravel(), axis=1)))]
        print(f"{f.name:34s} {st['frames']:3d} {st['mano_der']:4.0%} {st['mano_izq']:4.0%} "
              f"{st['hombros']:4.0%} {st['activa']:4.0%} {st['inicio']:4.0%} {st['fin']:4.0%}  "
              f"{top:24s} | {vecino}")

    print("\nDataset (promedio, ya remuestreado a 30 frames):")
    for k in ("mano_der", "mano_izq", "hombros", "activa", "inicio", "fin"):
        vals = [s[k] for s in ref_stats if s[k] >= 0]
        print(f"  {k:9s} {np.mean(vals):5.0%}")
    print("\nQué buscar:")
    print("  - 'izq' alto y 'der' bajo  -> se firmó con la otra mano (el dataset es con la DERECHA).")
    print("  - 'homb' bajo              -> no se ven los hombros: aléjate de la cámara.")
    print("  - 'fr' muy alto (>90)      -> la seña no se cerró: baja más las manos entre señas.")
    print("  - 'act' muy distinto al dataset -> encuadre/postura distintos a las grabaciones.")


if __name__ == "__main__":
    main()
