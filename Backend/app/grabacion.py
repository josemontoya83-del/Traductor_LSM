"""
Rutas de la GRABACIÓN EN EL NAVEGADOR (pantalla /grabar de la interfaz).

La persona sorda graba sola siguiendo la pantalla: el navegador graba el video con la cámara
(MediaRecorder) y, al mismo tiempo, manda imágenes pequeñas a /ws/revision para saber si se ve
bien a la persona y si tiene la mano levantada (así la toma empieza y termina sola).
Cada toma terminada se sube a POST /grabacion/toma y se guarda igual que con la captura clásica:
    datos/videos/P01/s1/<clip>.webm + <clip>.json

Variable LSM_REVISION=simulada: /ws/revision responde con un guion fijo (sin MediaPipe), para
probar la pantalla sin una persona frente a la cámara.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from lsm import puntos as P
from lsm.calidad import Revisor
from lsm.datos import borrar_toma, carpeta_sesion, guardar_participante, participantes
from lsm.protocolo import cargar_protocolo, tomas as lista_tomas

router = APIRouter()
PATRON_PERSONA = re.compile(r"^P\d{2,3}$")
MAX_VIDEO = 200 * 1024 * 1024   # 200 MB por toma: de sobra para 25 s de video


def _validar(persona: str, sesion: str) -> str:
    persona = persona.upper()
    if not PATRON_PERSONA.match(persona):
        raise HTTPException(400, "El código debe ser como P01 (nunca el nombre).")
    if sesion not in cargar_protocolo()["sesiones"]:
        raise HTTPException(400, f"La sesión {sesion} no existe en el protocolo.")
    return persona


def _bloques(bloques: str):
    return [b.strip().upper() for b in bloques.split(",") if b.strip()] or None


def _toma_por_nombre(persona: str, sesion: str, nombre: str):
    for t in lista_tomas(persona, sesion, incluir_opcionales=True):
        if t.nombre == nombre:
            return t
    raise HTTPException(400, "Esa toma no está en el protocolo.")


@router.get("/grabacion/protocolo")
def protocolo():
    prot = cargar_protocolo()
    sesiones = {}
    for s, bloques in prot["sesiones"].items():
        sesiones[s] = [dict(bloque=b["bloque"], nombre=b["nombre"], tipo=b["tipo"],
                            opcional=bool(b.get("opcional")),
                            tomas=len(lista_tomas("P00", s, bloques=[b["bloque"]])))
                       for b in bloques]
    return {"version": prot["version"], "cuenta_regresiva_s": prot["cuenta_regresiva_s"], "sesiones": sesiones}


@router.get("/grabacion/estado")
def estado(persona: str, sesion: str, bloques: str = "", opcionales: bool = False):
    persona = _validar(persona, sesion)
    lista = lista_tomas(persona, sesion, _bloques(bloques), incluir_opcionales=opcionales)
    carpeta = carpeta_sesion(persona, sesion)
    info = participantes().get(persona)
    return {
        "persona": persona, "sesion": sesion, "registrada": info is not None, "info": info,
        "cuenta_regresiva_s": cargar_protocolo()["cuenta_regresiva_s"],
        "tomas": [dict(t.__dict__, nombre=t.nombre, hecha=(carpeta / f"{t.nombre}.json").exists()) for t in lista],
    }


class Persona(BaseModel):
    persona: str
    mano_dominante: str = Field(pattern="^(derecha|izquierda)$")
    rango_edad: str = ""
    lsm_lengua_materna: Optional[bool] = None
    anos_usando_lsm: str = ""
    region: str = ""
    consentimiento: bool
    notas: str = ""


@router.post("/grabacion/persona")
def registrar(p: Persona):
    persona = _validar(p.persona, next(iter(cargar_protocolo()["sesiones"])))
    if not p.consentimiento:
        raise HTTPException(400, "Sin consentimiento firmado no se puede grabar.")
    info = p.model_dump(exclude={"persona"})
    previa = participantes().get(persona, {})
    info["fecha_registro"] = previa.get("fecha_registro", datetime.now().isoformat(timespec="seconds"))
    guardar_participante(persona, info)
    return {"ok": True, "persona": persona}


@router.post("/grabacion/toma")
async def subir_toma(persona: str = Form(...), sesion: str = Form(...), nombre: str = Form(...),
                     meta: str = Form("{}"), video: UploadFile = File(...)):
    persona = _validar(persona, sesion)
    toma = _toma_por_nombre(persona, sesion, nombre)
    tipo_mime = (video.content_type or "").lower()
    ext = ".mp4" if "mp4" in tipo_mime else ".webm"
    contenido = await video.read()
    if not contenido:
        raise HTTPException(400, "El video llegó vacío.")
    if len(contenido) > MAX_VIDEO:
        raise HTTPException(413, "El video es demasiado grande.")
    try:
        cliente = json.loads(meta)
    except json.JSONDecodeError:
        cliente = {}
    borrar_toma(persona, sesion, nombre)   # si se repite, reemplaza la anterior (en cualquier formato)
    carpeta = carpeta_sesion(persona, sesion)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{nombre}{ext}").write_bytes(contenido)
    info = participantes().get(persona, {})
    datos = dict(
        persona=persona, sesion=sesion, bloque=toma.bloque, tipo=toma.tipo, etiqueta=toma.etiqueta,
        texto=toma.texto, repeticion=toma.repeticion, movimiento=toma.movimiento, modo=toma.modo,
        mano_dominante=info.get("mano_dominante"), fecha=datetime.now().isoformat(timespec="seconds"),
        fuente="navegador", formato=tipo_mime or ext[1:], bytes=len(contenido),
        version_protocolo=cargar_protocolo()["version"],
        **{k: cliente[k] for k in ("ancho", "alto", "fps_camara", "duracion_s", "motivo_fin", "calidad", "navegador")
           if k in cliente})
    (carpeta / f"{nombre}.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "nombre": nombre}


@router.delete("/grabacion/toma")
def borrar(persona: str, sesion: str, nombre: str):
    persona = _validar(persona, sesion)
    _toma_por_nombre(persona, sesion, nombre)
    borrar_toma(persona, sesion, nombre)
    return {"ok": True}


class _RevisorSimulado:
    """Sin MediaPipe: persona bien encuadrada; al empezar a grabar levanta la mano 1.2 s y la baja."""

    def __init__(self) -> None:
        self._t_grabando: Optional[float] = None

    def fase(self, fase: str) -> None:
        self._t_grabando = time.monotonic() if fase == "grabando" else None

    def revisar_imagen(self, _img) -> dict:
        activa = self._t_grabando is not None and 0.3 < time.monotonic() - self._t_grabando < 1.5
        return {"encuadre": "ok", "hombros": True, "mano": activa, "activa": activa}

    def cerrar(self) -> None:
        pass


class _RevisorReal:
    def __init__(self) -> None:
        self._holistic = P.crear_holistic()
        self._revisor = Revisor()

    def fase(self, fase: str) -> None:
        pass

    def revisar_imagen(self, img) -> dict:
        return self._revisor.revisar(P.procesar_imagen(self._holistic, img))

    def cerrar(self) -> None:
        self._holistic.close()


@router.websocket("/ws/revision")
async def ws_revision(ws: WebSocket):
    """Entrada: imágenes JPEG (binario) y {"tipo": "fase", "fase": "..."}.
    Salida por imagen: {"encuadre": "ok|sin_persona|lejos|cerca|cabeza", "hombros", "mano", "activa"}."""
    await ws.accept()
    simulada = os.getenv("LSM_REVISION", "").lower() == "simulada"
    revisor = _RevisorSimulado() if simulada else await asyncio.to_thread(_RevisorReal)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes"):
                img = cv2.imdecode(np.frombuffer(msg["bytes"], np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    await ws.send_json({"encuadre": "sin_persona", "hombros": False, "mano": False, "activa": False})
                    continue
                await ws.send_json(await asyncio.to_thread(revisor.revisar_imagen, img))
            elif msg.get("text"):
                try:
                    datos = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if datos.get("tipo") == "fase":
                    revisor.fase(str(datos.get("fase", "")))
    except WebSocketDisconnect:
        pass
    finally:
        revisor.cerrar()
