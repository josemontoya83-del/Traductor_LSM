"""
entrenar_senas.py — Entrena el modelo de SEÑAS (palabras completas).

    python herramientas/entrenar_senas.py            # evalúa por persona y guarda modelos/senas.h5
    python herramientas/entrenar_senas.py --prueba   # prueba final con las personas apartadas

Usa los clips 'sena' de TODOS los dominios (general, escolar...) y los 'negativo' (_nada).
En vivo, el servidor solo deja ganar a las señas de 'general' + los dominios de esa ventanilla.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from lsm import modelos  # noqa: E402
from lsm.datos import listar_clips, personas_prueba  # noqa: E402
from lsm.entrenamiento import (aumentar_sena, ejemplos_senas, entrenar, informe, predecir,  # noqa: E402
                               validacion_cruzada)
from lsm.vocabulario import NADA, cargar as cargar_vocabulario  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true", help="evaluar el modelo guardado con las personas apartadas")
    ap.add_argument("--sin-validacion", action="store_true")
    ap.add_argument("--epocas", type=int, default=80)
    ap.add_argument("--copias", type=int, default=6, help="copias aumentadas por ejemplo")
    a = ap.parse_args()

    vocab = cargar_vocabulario()
    prueba = personas_prueba()
    clips = [c for c in listar_clips(["sena", "negativo"]) if c.puntos.exists()]

    if a.prueba:
        if not prueba:
            raise SystemExit("No hay personas de prueba en protocolo/particion.json.")
        if not modelos.existe("senas"):
            raise SystemExit("Primero entrena el modelo (sin --prueba).")
        modelo, meta = modelos.cargar("senas")
        clases = meta["clases"]
        X, y, g = ejemplos_senas([c for c in clips if c.persona in prueba])
        conocidas = np.isin(y, clases)
        informe(np.array([clases.index(e) for e in y[conocidas]]), predecir(modelo, X[conocidas]), clases,
                g[conocidas], "[PRUEBA FINAL] Señas con personas nunca vistas")
        return

    clips = [c for c in clips if c.persona not in prueba]
    if not clips:
        raise SystemExit("No hay clips de señas con puntos. Graba (captura.py) y corre extraer_puntos.py.")
    X, y, g = ejemplos_senas(clips)
    orden = [s["id"] for s in vocab.senas()]
    desconocidas = sorted(set(y) - set(orden) - {NADA})
    if desconocidas:
        print(f"  Aviso: señas grabadas que ya no están en el vocabulario (se ignoran): {desconocidas}")
    usar = np.isin(y, orden + [NADA])
    X, y, g = X[usar], y[usar], g[usar]
    clases = [c for c in orden if c in set(y)] + ([NADA] if NADA in set(y) else [])
    yi = np.array([clases.index(e) for e in y])
    print(f"Ejemplos: {len(X)} | personas: {sorted(set(g))} | clases: {len(clases)}")

    metricas = {}
    if not a.sin_validacion:
        metricas["por_persona"] = validacion_cruzada(
            X, yi, g, clases, modelos.construir_senas, aumentar_sena, a.copias, a.epocas,
            "[VALIDACIÓN] Señas dejando personas fuera (la métrica que importa)")

    modelo = entrenar(X, yi, g, len(clases), modelos.construir_senas, aumentar_sena, a.copias, a.epocas)
    dominio = {s["id"]: s["dominio"] for s in vocab.senas()}
    ruta = modelos.guardar(modelo, "senas", dict(clases=clases, dominios={c: dominio.get(c, "") for c in clases},
                                                 personas=sorted(set(g)), ejemplos=int(len(X)), metricas=metricas))
    print(f"\nModelo guardado en {ruta}")


if __name__ == "__main__":
    main()
