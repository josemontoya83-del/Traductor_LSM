"""
Servidor local de LSM-Connect (Edge: corre en la misma máquina de la ventanilla).

Arranque (desde la carpeta Backend/):
    uvicorn app.main:app --port 8000
    $env:LSM_MOTOR="real"; uvicorn app.main:app --port 8000      # con el modelo real (PowerShell)
"""
import asyncio
import os
import json
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .contrato import MensajeChat
from .motores import CLASES_DEFECTO, crear_motor

app = FastAPI(title="LSM-Connect")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])

MAX_TEXTO = 500
MAX_HISTORIAL = 50


class Salas:
    """Chat en memoria RAM (nada se guarda en disco). Una sala = una atención en ventanilla."""

    def __init__(self) -> None:
        self.conexiones: dict[str, set[WebSocket]] = defaultdict(set)
        self.historial: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORIAL))

    async def difundir(self, sala: str, datos: dict) -> None:
        for ws in list(self.conexiones[sala]):
            try:
                await ws.send_json(datos)
            except Exception:
                self.conexiones[sala].discard(ws)

    async def cerrar(self, sala: str) -> None:
        self.historial.pop(sala, None)
        await self.difundir(sala, {"tipo": "cerrada"})


salas = Salas()


@app.get("/salud")
def salud():
    return {"ok": True, "motor": os.getenv("LSM_MOTOR", "simulado")}


@app.get("/clases")
def clases():
    return {"clases": CLASES_DEFECTO}


@app.post("/chat/{sala}/cerrar")
async def cerrar_sala(sala: str):
    """Fin de la atención: borra la conversación de la RAM y avisa a los clientes."""
    await salas.cerrar(sala)
    return {"ok": True}


@app.websocket("/ws/camara")
async def ws_camara(ws: WebSocket):
    """Entrada: frames JPEG (binario). Salida: un ResultadoCamara (JSON) por frame."""
    await ws.accept()
    motor = crear_motor()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes"):
                resultado = await asyncio.to_thread(motor.procesar_frame, msg["bytes"])
                await ws.send_json(resultado.model_dump())
            elif msg.get("text"):
                try:
                    if json.loads(msg["text"]).get("tipo") == "reiniciar":
                        motor.reiniciar()
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket, rol: str = "estudiante", sala: str = "principal"):
    """Entrada: {"texto": "..."}. Salida: historial al conectar y cada mensaje de la sala."""
    await ws.accept()
    if rol not in ("estudiante", "ventanilla"):
        await ws.close(code=4400)
        return
    salas.conexiones[sala].add(ws)
    await ws.send_json({"tipo": "historial", "mensajes": list(salas.historial[sala])})
    try:
        while True:
            try:
                texto = str((await ws.receive_json()).get("texto", "")).strip()[:MAX_TEXTO]
            except (json.JSONDecodeError, AttributeError):
                continue
            if not texto:
                continue
            try:
                m = MensajeChat(rol=rol, texto=texto, hora=datetime.now(timezone.utc).isoformat())
            except ValidationError:
                continue
            datos = m.model_dump()
            salas.historial[sala].append(datos)
            await salas.difundir(sala, datos)
    except WebSocketDisconnect:
        pass
    finally:
        salas.conexiones[sala].discard(ws)
