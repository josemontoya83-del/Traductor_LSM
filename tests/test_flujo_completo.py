"""
Flujo completo con datos sintéticos: guardar clips -> ejemplos -> entrenar -> guardar modelos ->
motor en vivo (deletreo y señas, diestro y zurdo) -> evaluación del deletreo.
"""
import numpy as np
import pytest

import sinteticos as S
from lsm import modelos
from lsm.config import DIR_MODELOS
from lsm.datos import listar_clips
from lsm.entrenamiento import (aumentar_letra, aumentar_sena, ejemplos_letras, ejemplos_senas,
                               entrenar, validacion_cruzada)
from lsm.vocabulario import NADA

LETRAS = {"k": (11, False), "a": (12, False), "r": (13, False), "d": (14, False), "e": (15, False),
          "x": (16, True), "b": (17, False), "c": (18, False)}
SENAS = ["kardex", "beca", "gracias", "si"]
PERSONAS = {"P01": False, "P02": False, "P03": True}   # P03 es zurda


@pytest.fixture(scope="module")
def datos():
    for persona, zurdo in PERSONAS.items():
        semilla = int(persona[1:]) * 1000
        for rep in range(1, 4):
            for etiqueta, (s, mov) in LETRAS.items():
                S.guardar_clip(S.clip_letra(s, mov, zurdo=zurdo, semilla=semilla + rep * 37 + s),
                               persona, "1", "letra", etiqueta, rep)
            for k, etiqueta in enumerate(SENAS):
                S.guardar_clip(S.clip_sena(k, zurdo=zurdo, semilla=semilla + rep * 91 + k),
                               persona, "1", "sena", etiqueta, rep)
            S.guardar_clip(S.clip_negativo(zurdo=zurdo, semilla=semilla + rep), persona, "1", "negativo", "rascarse", rep)
        palabra = ["k", "a", "r", "d", "e", "x"]
        S.guardar_clip(S.clip_deletreo([LETRAS[l][0] for l in palabra], [LETRAS[l][1] for l in palabra],
                                       zurdo=zurdo, semilla=semilla + 5),
                       persona, "1", "deletreo", "kardex", 1, texto="KARDEX", modo="deletreo")
    return True


def _clips(tipos):
    """Solo las personas sintéticas de esta prueba (otras pruebas comparten la carpeta temporal)."""
    return [c for c in listar_clips(tipos) if c.persona in PERSONAS and c.puntos.exists()]


def _clases(y, orden):
    return [c for c in orden if c in set(y)] + [NADA]


def test_entrenar_y_reconocer_letras(datos):
    clips = _clips(["letra", "negativo"])
    X, y, g = ejemplos_letras(clips)
    clases = _clases(y, list(LETRAS))
    yi = np.array([clases.index(e) for e in y])
    assert set(g) == set(PERSONAS)
    res = validacion_cruzada(X, yi, g, clases, modelos.construir_letras, aumentar_letra, 1, 15, "letras")
    assert res["precision"] > 0.8, res          # incluye dejar fuera a la persona zurda
    modelo = entrenar(X, yi, g, len(clases), modelos.construir_letras, aumentar_letra, 1, 15)
    modelos.guardar(modelo, "letras", {"clases": clases})


def test_entrenar_y_reconocer_senas(datos):
    X, y, g = ejemplos_senas(_clips(["sena", "negativo"]))
    clases = _clases(y, SENAS)
    yi = np.array([clases.index(e) for e in y])
    modelo = entrenar(X, yi, g, len(clases), modelos.construir_senas, aumentar_sena, 3, 25)
    acc = np.mean(modelo.predict(X, verbose=0).argmax(1) == yi)
    assert acc > 0.8, acc
    modelos.guardar(modelo, "senas", {"clases": clases})


def test_motor_en_vivo_deletreo_y_senas(datos):
    from lsm import puntos as P
    from lsm.motor import MotorLSM

    motor = MotorLSM(carpeta_modelos=DIR_MODELOS)
    # deletreo, diestro y zurdo
    for zurdo in (False, True):
        motor.configurar("deletreo", ["escolar"])
        palabra = ["k", "a", "r", "d", "e", "x"]
        clip = S.clip_deletreo([LETRAS[l][0] for l in palabra], [LETRAS[l][1] for l in palabra],
                               zurdo=zurdo, semilla=99, fps=15)
        finales = [r for i, t in enumerate(clip["t"])
                   if (r := motor.procesar_cuadro(P.cuadro(clip, i), float(t))).estado in ("palabra", "duda")]
        assert finales, "no se cerró la palabra"
        opciones = [finales[-1].palabra] + [c["palabra"] for c in finales[-1].top3]
        assert "Kárdex" in opciones, finales[-1]
    # señas: la ventanilla escolar reconoce 'kardex'
    motor.configurar("senas", ["escolar"])
    clip = S.clip_sena(0, semilla=4242, fps=15)
    res = [r for i, t in enumerate(clip["t"])
           if (r := motor.procesar_cuadro(P.cuadro(clip, i), float(t))).estado in ("palabra", "duda")]
    assert res and res[-1].top3[0]["palabra"] == "Kárdex", res
    # un movimiento sin significado no escribe nada
    motor.configurar("senas", ["escolar"])
    clip = S.clip_negativo(semilla=31337, fps=15)
    res = [motor.procesar_cuadro(P.cuadro(clip, i), float(t)) for i, t in enumerate(clip["t"])]
    assert not [r for r in res if r.estado == "palabra"]


def test_evaluar_deletreo(datos):
    import importlib

    el = importlib.import_module("herramientas.entrenar_letras")
    r = el.evaluar_deletreo(_clips(["deletreo"]), "prueba")
    assert r["corregidas"] == 1.0, r


def test_modelo_con_otra_version_se_rechaza(tmp_path):
    import json

    from lsm.config import DIR_MODELOS
    import shutil

    shutil.copy(DIR_MODELOS / "letras.h5", tmp_path / "letras.h5")
    meta = json.loads((DIR_MODELOS / "letras.json").read_text())
    meta["version_extractor"] = "otra"
    (tmp_path / "letras.json").write_text(json.dumps(meta))
    with pytest.raises(RuntimeError):
        modelos.cargar("letras", tmp_path)
