"""Rutas de la grabación en el navegador (Backend/app/grabacion.py)."""
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from lsm.config import DIR_PUNTOS, DIR_VIDEOS
from lsm.datos import listar_clips
from lsm.protocolo import tomas


@pytest.fixture()
def cliente(monkeypatch):
    monkeypatch.setenv("LSM_MOTOR", "simulado")
    import app.main as m

    return TestClient(m.app)


def test_protocolo_y_estado(cliente):
    prot = cliente.get("/grabacion/protocolo").json()
    assert sum(b["tomas"] for b in prot["sesiones"]["1"]) == 263
    e = cliente.get("/grabacion/estado", params={"persona": "p21", "sesion": "1"}).json()
    assert e["persona"] == "P21" and not e["registrada"] and len(e["tomas"]) == 263
    assert not any(t["hecha"] for t in e["tomas"])
    assert any(t["pista"] for t in e["tomas"])          # las palabras ambiguas traen pista
    g = cliente.get("/grabacion/estado", params={"persona": "P21", "sesion": "2", "bloques": "G", "opcionales": True}).json()
    assert {t["tipo"] for t in g["tomas"]} == {"respuesta"}


@pytest.mark.parametrize("persona", ["../x", "Juan", "P1", "P01/../../etc"])
def test_codigo_invalido_se_rechaza(cliente, persona):
    assert cliente.get("/grabacion/estado", params={"persona": persona, "sesion": "1"}).status_code == 400


def test_registro_requiere_consentimiento(cliente):
    r = cliente.post("/grabacion/persona", json={"persona": "P21", "mano_dominante": "derecha", "consentimiento": False})
    assert r.status_code == 400
    r = cliente.post("/grabacion/persona", json={"persona": "P21", "mano_dominante": "zurda", "consentimiento": True})
    assert r.status_code == 422
    r = cliente.post("/grabacion/persona", json={"persona": "P21", "mano_dominante": "izquierda", "consentimiento": True})
    assert r.status_code == 200
    e = cliente.get("/grabacion/estado", params={"persona": "P21", "sesion": "1"}).json()
    assert e["registrada"] and e["info"]["mano_dominante"] == "izquierda"


def test_subir_repetir_y_borrar_toma(cliente):
    nombre = tomas("P21", "1")[0].nombre
    meta = {"duracion_s": 3.2, "motivo_fin": "manos_abajo", "calidad": {"avisos": []}, "persona": "P99",
            "tipo": "hackeado"}
    datos = {"persona": "P21", "sesion": "1", "nombre": nombre, "meta": json.dumps(meta)}
    r = cliente.post("/grabacion/toma", data=datos, files={"video": ("x.webm", b"webm-falso", "video/webm")})
    assert r.status_code == 200, r.text
    carpeta = DIR_VIDEOS / "P21" / "s1"
    guardado = json.loads((carpeta / f"{nombre}.json").read_text(encoding="utf-8"))
    assert guardado["persona"] == "P21" and guardado["tipo"] != "hackeado"   # el servidor no confía en el cliente
    assert guardado["mano_dominante"] == "izquierda" and guardado["fuente"] == "navegador"
    assert (carpeta / f"{nombre}.webm").read_bytes() == b"webm-falso"
    assert any(c.json.stem == nombre and c.video.suffix == ".webm" for c in listar_clips())
    assert cliente.get("/grabacion/estado", params={"persona": "P21", "sesion": "1"}).json()["tomas"][0]["hecha"]

    # repetir: reemplaza en cualquier formato y borra los puntos viejos
    (DIR_PUNTOS / "P21" / "s1").mkdir(parents=True, exist_ok=True)
    (DIR_PUNTOS / "P21" / "s1" / f"{nombre}.npz").write_bytes(b"viejo")
    r = cliente.post("/grabacion/toma", data=datos, files={"video": ("x.mp4", b"mp4-falso", "video/mp4")})
    assert r.status_code == 200
    assert not (carpeta / f"{nombre}.webm").exists() and (carpeta / f"{nombre}.mp4").exists()
    assert not (DIR_PUNTOS / "P21" / "s1" / f"{nombre}.npz").exists()

    assert cliente.delete("/grabacion/toma", params={"persona": "P21", "sesion": "1", "nombre": nombre}).status_code == 200
    assert not list(carpeta.glob(f"{nombre}.*"))


def test_toma_fuera_del_protocolo_o_vacia(cliente):
    base = {"persona": "P21", "sesion": "1"}
    r = cliente.post("/grabacion/toma", data={**base, "nombre": "../../malo"},
                     files={"video": ("x.webm", b"x", "video/webm")})
    assert r.status_code == 400
    nombre = tomas("P21", "1")[0].nombre
    r = cliente.post("/grabacion/toma", data={**base, "nombre": nombre}, files={"video": ("x.webm", b"", "video/webm")})
    assert r.status_code == 400


def _jpeg():
    return cv2.imencode(".jpg", np.zeros((360, 640, 3), np.uint8))[1].tobytes()


def test_ws_revision_simulada(cliente, monkeypatch):
    monkeypatch.setenv("LSM_REVISION", "simulada")
    with cliente.websocket_connect("/ws/revision") as ws:
        ws.send_bytes(_jpeg())
        assert ws.receive_json() == {"encuadre": "ok", "hombros": True, "mano": False, "activa": False}
        ws.send_text('{"tipo": "fase", "fase": "grabando"}')
        import time

        time.sleep(0.5)
        ws.send_bytes(_jpeg())
        assert ws.receive_json()["activa"] is True


def test_ws_revision_real_sin_persona(cliente, monkeypatch):
    monkeypatch.delenv("LSM_REVISION", raising=False)
    with cliente.websocket_connect("/ws/revision") as ws:
        ws.send_bytes(_jpeg())
        r = ws.receive_json()
        assert r["encuadre"] == "sin_persona" and r["activa"] is False
        ws.send_bytes(b"no es imagen")
        assert ws.receive_json()["encuadre"] == "sin_persona"
