"""
entrenar_letras.py — Entrena el modelo de DELETREO (letras y números).

    python herramientas/entrenar_letras.py            # evalúa por persona y guarda modelos/letras.h5
    python herramientas/entrenar_letras.py --prueba   # prueba final con las personas apartadas

Usa los clips 'letra', 'numero' y 'negativo' (este último enseña la clase _nada). Al final
reproduce las palabras deletreadas (bloque E) por el MISMO motor del servidor y mide qué tan
bien se reconstruye cada palabra.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from lsm import modelos, puntos as P  # noqa: E402
from lsm.config import DIR_MODELOS  # noqa: E402
from lsm.datos import listar_clips, personas_prueba  # noqa: E402
from lsm.decodificador import levenshtein  # noqa: E402
from lsm.entrenamiento import (aumentar_letra, ejemplos_letras, entrenar, informe, predecir,  # noqa: E402
                               validacion_cruzada)
from lsm.vocabulario import NADA, cargar as cargar_vocabulario, normalizar  # noqa: E402


def evaluar_deletreo(clips, titulo: str, carpeta=DIR_MODELOS) -> dict:
    """Pasa cada palabra deletreada por el motor en vivo y compara con la palabra esperada."""
    from lsm.motor import MotorLSM

    if not clips:
        return {}
    motor = MotorLSM(carpeta_modelos=carpeta)
    todos = list(motor.vocab.dominios)
    errores, letras, exactas, corregidas = 0, 0, 0, 0
    print(f"\n{titulo}")
    for clip in clips:
        motor.configurar(clip.meta.get("modo") or "deletreo", todos)
        datos = P.cargar(clip.puntos)
        crudo, final = "", None
        for i, t in enumerate(datos["t"]):
            r = motor.procesar_cuadro(P.cuadro(datos, i), float(t))
            crudo = r.parcial or crudo
            if r.estado in ("palabra", "duda"):
                final = r
                break
        if final is None:
            final = motor.terminar()
        esperado = normalizar(clip.meta["texto"])
        d = levenshtein(normalizar(crudo), esperado)
        errores += d
        letras += len(esperado)
        exactas += d == 0
        opciones = [normalizar(c["palabra"]) for c in (final.top3 if final else [])]
        if final and final.palabra:
            opciones.insert(0, normalizar(final.palabra))
        corregidas += esperado in opciones
        print(f"  {clip.persona} {clip.meta['texto']:>12s} -> {crudo or '(nada)':12s} "
              f"{'OK' if esperado in opciones else ''}")
    n = len(clips)
    print(f"  Error por letra: {errores / max(letras, 1):.1%} | palabras exactas: {exactas / n:.1%} "
          f"| correcta (con vocabulario/opciones): {corregidas / n:.1%}")
    return dict(error_letra=round(errores / max(letras, 1), 4), exactas=round(exactas / n, 4),
                corregidas=round(corregidas / n, 4))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true", help="evaluar el modelo guardado con las personas apartadas")
    ap.add_argument("--sin-validacion", action="store_true", help="no hacer la validación por persona (más rápido)")
    ap.add_argument("--epocas", type=int, default=60)
    ap.add_argument("--copias", type=int, default=2, help="copias aumentadas por ejemplo")
    a = ap.parse_args()

    vocab = cargar_vocabulario()
    prueba = personas_prueba()
    clips = [c for c in listar_clips(["letra", "numero", "negativo"]) if c.puntos.exists()]
    deletreo = [c for c in listar_clips(["deletreo"]) if c.puntos.exists()]

    if a.prueba:
        if not prueba:
            raise SystemExit("No hay personas de prueba en protocolo/particion.json.")
        if not modelos.existe("letras"):
            raise SystemExit("Primero entrena el modelo (sin --prueba).")
        modelo, meta = modelos.cargar("letras")
        clases = meta["clases"]
        X, y, g = ejemplos_letras([c for c in clips if c.persona in prueba
                                   and (c.tipo == "negativo" or c.etiqueta in clases)])
        informe(np.array([clases.index(e) for e in y]), predecir(modelo, X), clases, g,
                "[PRUEBA FINAL] Letras con personas nunca vistas")
        evaluar_deletreo([c for c in deletreo if c.persona in prueba], "[PRUEBA FINAL] Palabras deletreadas")
        return

    clips = [c for c in clips if c.persona not in prueba]
    if not clips:
        raise SystemExit("No hay clips de letras con puntos. Graba (captura.py) y corre extraer_puntos.py.")
    X, y, g = ejemplos_letras(clips)
    orden = [l["id"] for l in vocab.letras + vocab.numeros]
    clases = [c for c in orden if c in set(y)] + ([NADA] if NADA in set(y) else [])
    yi = np.array([clases.index(e) for e in y])
    print(f"Ejemplos: {len(X)} | personas: {sorted(set(g))} | clases: {len(clases)}")
    if NADA not in clases:
        print("  Aviso: no hay clips 'negativo'; el modelo no aprenderá a ignorar movimientos sin significado.")

    metricas = {}
    if not a.sin_validacion:
        metricas["por_persona"] = validacion_cruzada(
            X, yi, g, clases, modelos.construir_letras, aumentar_letra, a.copias, a.epocas,
            "[VALIDACIÓN] Letras dejando personas fuera (la métrica que importa)")

    modelo = entrenar(X, yi, g, len(clases), modelos.construir_letras, aumentar_letra, a.copias, a.epocas)
    ruta = modelos.guardar(modelo, "letras", dict(clases=clases, personas=sorted(set(g)),
                                                  ejemplos=int(len(X)), metricas=metricas))
    print(f"\nModelo guardado en {ruta}")
    evaluar_deletreo([c for c in deletreo if c.persona not in prueba],
                     "[OPTIMISTA] Palabras deletreadas de personas que sí se usaron al entrenar")


if __name__ == "__main__":
    main()
