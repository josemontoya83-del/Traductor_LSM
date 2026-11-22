"""
Servidor local de LSM-Connect (corre en la misma computadora de la ventanilla; nada sale a internet).

Arranque, desde la carpeta del proyecto:
    python -m uvicorn app.main:app --app-dir Backend --port 8000              # motor simulado
    $env:LSM_MOTOR="real"; python -m uvicorn app.main:app --app-dir Backend --port 8000   # modelos reales
"""
import asyncio
import json
import os
import threading
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from lsm import modelos
from lsm.vocabulario import cargar as cargar_vocabulario

from .contrato import ConfigCamara, ResultadoCamara
from .grabacion import router as router_grabacion

_MODELOS_LOCK = threading.Lock()
_BASE = None   # MotorLSM "plantilla": los modelos se cargan una vez y se comparten entre conexiones


def usa_motor_real() -> bool:
    return os.getenv("LSM_MOTOR", "simulado").lower() == "real"


def crear_motor():
    """Un motor por conexión de cámara (cada una tiene su propio segmentador y MediaPipe)."""
    global _BASE
    from lsm.motor import MotorLSM, MotorSimulado

    if not usa_motor_real():
        return MotorSimulado()
    with _MODELOS_LOCK:
        if _BASE is None:
            _BASE = MotorLSM()
    return MotorLSM(base=_BASE)


def precargar() -> None:
    """Deja listos modelos y MediaPipe al arrancar (si no, la primera conexión tarda ~30 s)."""
    if not usa_motor_real():
        return
    motor = crear_motor()
    motor.procesar_imagen(np.zeros((480, 640, 3), np.uint8))
    for m in (motor.m_senas, motor.m_letras):
        if m is not None:
            m(np.zeros((1, *m.input_shape[1:]), np.float32), training=False)
    motor.cerrar()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    await asyncio.to_thread(precargar)
    yield


app = FastAPI(title="LSM-Connect", lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router_grabacion)


@app.get("/salud")
def salud():
    return {"ok": True, "motor": "real" if usa_motor_real() else "simulado",
            "modelos": {"senas": modelos.existe("senas"), "letras": modelos.existe("letras")}}


@app.get("/vocabulario")
def vocabulario(dominios: str = Query("", description="separados por coma, p. ej. escolar")):
    """Lo que la interfaz necesita mostrar para esta ventanilla."""
    v = cargar_vocabulario()
    activos = v.dominios_activos([d for d in dominios.split(",") if d])
    return {
        "dominios_disponibles": [{"id": d, "nombre": c["nombre"]} for d, c in v.dominios.items()],
        "dominios_activos": activos,
        "senas": v.senas(activos),
        "respuestas": v.respuestas_de(activos),
    }


@app.websocket("/ws/camara")
async def ws_camara(ws: WebSocket):
    """Entrada: imágenes JPEG (binario) y mensajes de texto de control. Salida: un
    ResultadoCamara (JSON) por imagen."""
    await ws.accept()
    try:
        motor = await asyncio.to_thread(crear_motor)
    except Exception as e:  # p. ej. no hay modelos entrenados
        await ws.send_json(ResultadoCamara(aviso=str(e)).model_dump())
        await ws.close()
        return
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes"):
                img = cv2.imdecode(np.frombuffer(msg["bytes"], np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    await ws.send_json(ResultadoCamara().model_dump())
                    continue
                r = await asyncio.to_thread(motor.procesar_imagen, img)
                await ws.send_json(ResultadoCamara(**r.a_dict()).model_dump())
            elif msg.get("text"):
                try:
                    datos = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if datos.get("tipo") == "reiniciar":
                    motor.reiniciar()
                elif datos.get("tipo") == "config":
                    try:
                        cfg = ConfigCamara(**datos)
                    except ValidationError:
                        continue
                    motor.configurar(cfg.modo, cfg.dominios)
    except WebSocketDisconnect:
        pass
    finally:
        motor.cerrar()
