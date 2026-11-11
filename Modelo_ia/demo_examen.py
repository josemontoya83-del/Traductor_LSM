"""
demo_examen.py
Demo del componente crítico de LSM-Connect para el Examen 2 (sin depender de la cámara).

Dos modos (correr desde la raíz del repo, con el venv activo):

  python Modelo_ia/demo_examen.py evaluar
      Entrena con repeticiones 1-6 y prueba con 7-12 (misma metodología que entrenar_modelo.py)
      y reporta: precisión por seña y Levenshtein sobre frases de 3-5 señas.
      Guarda Modelo_ia/resultados_demo.json y Modelo_ia/matriz_confusion.png (para las diapositivas).

  python Modelo_ia/demo_examen.py replay --frase "inscripcion foto credencial"
      Reproduce grabaciones reales de esas señas por el MISMO motor que usa el backend
      (segmentación + modelo + umbral de duda). Es el respaldo si la cámara falla en el examen.
      Requiere Modelo_ia/lsm_tramites.h5 (python Modelo_ia/entrenar_modelo.py --guardar).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "Modelo_ia"))
sys.path.insert(0, str(RAIZ / "Backend"))

from entrenar_modelo import CLASES, DATA_DIR, cargar_dataset, entrenar, top_k  # noqa: E402

SENAS = [c for c in CLASES if c != "reposo"]


def levenshtein(a: list, b: list) -> int:
    """Distancia de edición entre dos listas de palabras (inserciones, borrados, sustituciones)."""
    previa = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        actual = [i]
        for j, y in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (x != y)))
        previa = actual
    return previa[-1]


def evaluar_frases(y_real, y_pred, n_frases=300, semilla=7):
    """Arma frases al azar de 3-5 señas con muestras de prueba y mide Levenshtein."""
    rng = np.random.default_rng(semilla)
    por_clase = {c: np.where(y_real == CLASES.index(c))[0] for c in SENAS}
    por_clase = {c: idx for c, idx in por_clase.items() if len(idx)}
    nombres = list(por_clase)
    dist_total, largo_total, exactas = 0, 0, 0
    for _ in range(n_frases):
        n = int(rng.integers(3, 6))
        real, pred = [], []
        for c in rng.choice(nombres, size=n):
            i = int(rng.choice(por_clase[c]))
            real.append(c)
            pred.append(CLASES[y_pred[i]])
        d = levenshtein(real, pred)
        dist_total += d
        largo_total += n
        exactas += d == 0
    return {
        "frases": n_frases,
        "distancia_media": round(dist_total / n_frases, 3),
        "word_error_rate": round(dist_total / largo_total, 3),
        "frases_exactas": round(exactas / n_frases, 3),
    }


def matriz_png(y_real, y_pred, ruta: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(CLASES)
    m = np.zeros((n, n), int)
    for a, b in zip(y_real, y_pred):
        m[a, b] += 1
    m = m / np.maximum(m.sum(1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.imshow(m, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(n), CLASES, rotation=60, ha="right")
    ax.set_yticks(range(n), CLASES)
    ax.set_xlabel("Predicho")
    ax.set_ylabel("Real")
    ax.set_title("Matriz de confusión (prueba, reps 7-12)")
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)


def modo_evaluar() -> None:
    X, y, personas, numeros = cargar_dataset()
    tr, te = numeros <= 6, (numeros >= 7) & (numeros <= 12)
    print(f"Muestras: {len(X)} | Personas: {sorted(set(personas))} | Clases: {len(CLASES)}")
    modelo = entrenar("gru", X[tr], y[tr])
    prob = modelo.predict(X[te], verbose=0)
    real, pred = y[te], prob.argmax(1)
    res = {
        "muestras_prueba": int(te.sum()),
        "precision_top1": round(float(np.mean(real == pred)), 3),
        "precision_top3": round(top_k(prob, real), 3),
        "frases": evaluar_frases(real, pred),
        "nota": "Prueba con personas ya vistas (reps 7-12). Con una persona nueva baja mucho: ver README.",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    (RAIZ / "Modelo_ia" / "resultados_demo.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                                                encoding="utf-8")
    matriz_png(real, pred, RAIZ / "Modelo_ia" / "matriz_confusion.png")
    print("\nGuardado: Modelo_ia/resultados_demo.json y Modelo_ia/matriz_confusion.png")


def modo_replay(frase: str, persona: str, rep: int) -> None:
    import os

    os.environ["LSM_MOTOR"] = "real"
    from app.motores import MotorReal  # el mismo motor del backend

    motor = MotorReal()
    palabras = frase.split()
    t, salida = 0.0, []
    print(f"Frase real: {' '.join(palabras)}\n")
    for p in palabras:
        archivos = sorted((DATA_DIR / p).glob(f"{persona}_*.npy"))
        if not archivos:
            sys.exit(f"No hay grabaciones de '{p}' para '{persona}'. Cambia --persona.")
        seq = np.load(archivos[min(rep - 1, len(archivos) - 1)])
        for frame in seq:                       # la seña, a 30 fps
            motor.procesar_vector(frame, t)
            t += 1 / 30
        quieto = np.zeros(226)
        quieto[126:] = seq[0][126:]             # cuerpo visible, manos abajo
        for _ in range(25):                     # pausa: cierra la seña y predice
            r = motor.procesar_vector(quieto, t)
            t += 1 / 30
            if r.estado in ("palabra", "duda"):
                top = ", ".join(f"{c.palabra} {c.prob:.0%}" for c in r.top3)
                marca = "PALABRA" if r.estado == "palabra" else "DUDA   "
                print(f"  seña '{p}' -> {marca} ({top})")
                salida.append(r.palabra if r.estado == "palabra" else r.top3[0].palabra)
    d = levenshtein(palabras, salida)
    print(f"\nTraducción: {' '.join(salida)}")
    print(f"Distancia de Levenshtein: {d} (0 = frase perfecta)")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="modo", required=True)
    sub.add_parser("evaluar")
    r = sub.add_parser("replay")
    r.add_argument("--frase", required=True)
    r.add_argument("--persona", default="mau")
    r.add_argument("--rep", type=int, default=10, help="número de repetición (usa una de 7-12)")
    a = ap.parse_args()
    modo_evaluar() if a.modo == "evaluar" else modo_replay(a.frase, a.persona, a.rep)


if __name__ == "__main__":
    main()