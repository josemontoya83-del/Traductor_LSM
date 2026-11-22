import cv2
import numpy as np
from fastapi.testclient import TestClient


def _cliente(monkeypatch, motor="simulado"):
    monkeypatch.setenv("LSM_MOTOR", motor)
    import app.main as m

    m._BASE = None
    return TestClient(m.app)


def _jpeg():
    return cv2.imencode(".jpg", np.zeros((480, 640, 3), np.uint8))[1].tobytes()


def test_salud_y_vocabulario(monkeypatch):
    with _cliente(monkeypatch) as c:
        assert c.get("/salud").json()["ok"]
        v = c.get("/vocabulario", params={"dominios": "escolar"}).json()
        assert v["dominios_activos"] == ["general", "escolar"]
        ids = {s["id"] for s in v["senas"]}
        assert {"gracias", "kardex"} <= ids
        assert any(r["id"] == "pase_caja" for r in v["respuestas"])
        solo_general = c.get("/vocabulario").json()
        assert "kardex" not in {s["id"] for s in solo_general["senas"]}


def test_ws_camara_simulado_senas_y_deletreo(monkeypatch):
    with _cliente(monkeypatch) as c, c.websocket_connect("/ws/camara") as ws:
        ws.send_text('{"tipo": "config", "modo": "senas", "dominios": ["escolar"]}')
        estados = set()
        for _ in range(61):
            ws.send_bytes(_jpeg())
            estados.add(ws.receive_json()["estado"])
        assert {"reposo", "firmando", "palabra"} <= estados
        ws.send_text('{"tipo": "config", "modo": "deletreo", "dominios": ["escolar"]}')
        vistos = []
        for _ in range(61):
            ws.send_bytes(_jpeg())
            vistos.append(ws.receive_json())
        assert any(r["estado"] == "letra" and r["parcial"] for r in vistos)
        assert any(r["estado"] == "palabra" and r["palabra"] == "Kárdex" for r in vistos)
        ws.send_text("no es json")           # mensajes basura no rompen la conexión
        ws.send_text('{"tipo": "config", "modo": "inventado"}')
        ws.send_bytes(b"no es imagen")
        assert ws.receive_json()["estado"] == "reposo"


def test_ws_camara_motor_real_con_modelos(monkeypatch):
    """Usa los modelos que dejó test_flujo_completo (si se corrió antes)."""
    from lsm import modelos

    if not (modelos.existe("letras") and modelos.existe("senas")):
        import pytest

        pytest.skip("requiere los modelos de test_flujo_completo")
    with _cliente(monkeypatch, "real") as c:
        assert c.get("/salud").json()["modelos"] == {"senas": True, "letras": True}
        with c.websocket_connect("/ws/camara") as ws:
            ws.send_text('{"tipo": "config", "modo": "deletreo", "dominios": ["escolar"]}')
            for _ in range(3):
                ws.send_bytes(_jpeg())
                r = ws.receive_json()
                assert r["estado"] == "reposo" and r["aviso"] is None
