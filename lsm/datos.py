"""
Organización de los datos grabados.

    datos/
      participantes.json            P01 -> mano dominante, rango de edad... (SIN nombres)
      videos/P01/s1/<clip>.mp4      video original (se conserva: permite re-extraer en el futuro)
      videos/P01/s1/<clip>.json     metadatos: tipo, etiqueta, repetición, tiempos de cada cuadro...
      puntos/P01/s1/<clip>.npz      puntos de MediaPipe (lo genera herramientas/extraer_puntos.py)

Nombre de un clip: <tipo>__<etiqueta>__r<repetición>, p. ej. sena__kardex__r03.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import ARCHIVO_PARTICIPANTES, DIR_PROTOCOLO, DIR_PUNTOS, DIR_VIDEOS


def nombre_clip(tipo: str, etiqueta: str, repeticion: int) -> str:
    return f"{tipo}__{etiqueta}__r{repeticion:02d}"


def carpeta_sesion(persona: str, sesion: str, base: Path = DIR_VIDEOS) -> Path:
    return base / persona / f"s{sesion}"


@dataclass
class Clip:
    meta: dict
    json: Path

    @property
    def video(self) -> Path:
        return self.json.with_suffix(".mp4")

    @property
    def puntos(self) -> Path:
        return carpeta_sesion(self.persona, self.sesion, DIR_PUNTOS) / (self.json.stem + ".npz")

    persona = property(lambda self: self.meta["persona"])
    sesion = property(lambda self: str(self.meta["sesion"]))
    tipo = property(lambda self: self.meta["tipo"])
    etiqueta = property(lambda self: self.meta["etiqueta"])


def listar_clips(tipos=None, base: Path = DIR_VIDEOS) -> list[Clip]:
    clips = []
    for ruta in sorted(base.glob("*/s*/*.json")):
        meta = json.loads(ruta.read_text(encoding="utf-8"))
        if tipos is None or meta.get("tipo") in tipos:
            clips.append(Clip(meta, ruta))
    return clips


def participantes() -> dict:
    if ARCHIVO_PARTICIPANTES.exists():
        return json.loads(ARCHIVO_PARTICIPANTES.read_text(encoding="utf-8"))
    return {}


def guardar_participantes(datos: dict) -> None:
    ARCHIVO_PARTICIPANTES.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_PARTICIPANTES.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def personas_prueba() -> set[str]:
    """Personas apartadas para la prueba final (protocolo/particion.json). Nunca se entrena con ellas."""
    ruta = DIR_PROTOCOLO / "particion.json"
    if not ruta.exists():
        return set()
    return set(json.loads(ruta.read_text(encoding="utf-8")).get("prueba", []))
