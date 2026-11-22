"""Prueba del programa de captura sin ventana: un video falso hace de cámara."""
import dataclasses
import json
import time

import cv2
import numpy as np
import pytest

from herramientas.captura import Camara, SesionCaptura
from lsm.protocolo import tomas


@pytest.fixture(scope="module")
def video_falso(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("cam") / "falso.mp4"
    w = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 360))
    rng = np.random.default_rng(0)
    for i in range(90):
        img = np.full((360, 640, 3), 80, np.uint8)
        cv2.circle(img, (320 + int(50 * np.sin(i / 5)), 180), 40, (200, 180, 160), -1)
        w.write(img + rng.integers(0, 10, img.shape, dtype=np.uint8))
    w.release()
    return ruta


def _hasta(sesion, estado, limite=8.0):
    t0 = time.monotonic()
    while sesion.estado != estado and time.monotonic() - t0 < limite:
        img = sesion.paso()
    assert sesion.estado == estado, sesion.estado
    return img


def test_sesion_de_captura(video_falso):
    lista = [dataclasses.replace(t, segundos_max=0.8) for t in tomas("P99", "1")[:3]]
    cam = Camara(str(video_falso))
    try:
        s = SesionCaptura("P99", "1", lista, cam, {"mano_dominante": "derecha"}, "prueba")
        s.prot = dict(s.prot, cuenta_regresiva_s=0.3)
        img = s.paso()
        assert img.shape[1] == 1280 and img.ndim == 3

        primera = s.actual
        s.tecla(32)                                  # ESPACIO: cuenta regresiva + graba
        assert s.estado == "cuenta"
        _hasta(s, "grabando")
        _hasta(s, "espera")                          # se detiene sola por tiempo
        meta = json.loads((s.carpeta / f"{primera.nombre}.json").read_text(encoding="utf-8"))
        assert meta["persona"] == "P99" and meta["tipo"] == primera.tipo
        assert meta["n_cuadros"] == len(meta["tiempos"]) >= 20
        assert meta["motivo_fin"] == "tiempo"
        assert any("mano" in a for a in meta["calidad"]["avisos"])   # no hay persona: debe avisar
        cap = cv2.VideoCapture(str(s.carpeta / f"{primera.nombre}.mp4"))
        assert abs(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - meta["n_cuadros"]) <= 1
        cap.release()
        assert s.hechas == 1 and s.aviso_ultima

        from herramientas.extraer_puntos import extraer_video   # la extracción offline lee ese video
        datos = extraer_video(s.carpeta / f"{primera.nombre}.mp4", meta["tiempos"])
        assert len(datos["t"]) == datos["pose"].shape[0] and abs(len(datos["t"]) - meta["n_cuadros"]) <= 1
        assert np.allclose(datos["t"][:5], meta["tiempos"][:5])

        s.tecla(ord("r"))                            # repetir: borra y la vuelve a pedir
        assert s.actual == primera and s.hechas == 0
        assert not (s.carpeta / f"{primera.nombre}.json").exists()

        s.tecla(32)
        _hasta(s, "grabando")
        s.tecla(32)                                  # ESPACIO durante la grabación: la termina
        assert s.estado == "espera" and s.hechas == 1

        segunda = s.actual
        s.tecla(ord("s"))                            # saltar
        assert s.actual != segunda and s.pendientes[-1] == segunda

        s.tecla(32)
        s.tecla(ord("x"))                            # cancelar: no deja archivos
        assert s.estado == "espera" and s.hechas == 1
        assert not list(s.carpeta.glob(f"{s.actual.nombre}.*"))
        s.tecla(ord("q"))
        assert s.salir
        s.cerrar()

        retomada = SesionCaptura("P99", "1", lista, cam, {}, "prueba")   # al volver, continúa
        assert retomada.hechas == 1 and len(retomada.pendientes) == 2
        retomada.cerrar()
    finally:
        cam.cerrar()
