"""
Organización de los datos grabados.

    datos/
      participantes/P01.json        mano dominante, rango de edad... de cada persona (SIN nombres)
      videos/P01/s1/<clip>.mp4      video original (.mp4 de la captura clásica o .webm del navegador)
      videos/P01/s1/<clip>.json     metadatos: tipo, etiqueta, repetición, tiempos de cada cuadro...
      puntos/P01/s1/<clip>.npz      puntos de MediaPipe (lo genera herramientas/extraer_puntos.py)

Nombre de un clip: <tipo>__<etiqueta>__r<repetición>, p. ej. sena__kardex__r03.

Cada persona tiene sus propias carpetas y su propio archivo de participante: se puede grabar en
varias computadoras a la vez y después juntar las carpetas datos/ sin que choquen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import DIR_PARTICIPANTES, DIR_PROTOCOLO, DIR_PUNTOS, DIR_VIDEOS

EXTENSIONES_VIDEO = (".mp4", ".webm")


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
        for ext in EXTENSIONES_VIDEO:
            if self.json.with_suffix(ext).exists():
                return self.json.with_suffix(ext)
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
    """codigo -> datos de la persona."""
    if not DIR_PARTICIPANTES.exists():
        return {}
    return {r.stem: json.loads(r.read_text(encoding="utf-8")) for r in sorted(DIR_PARTICIPANTES.glob("P*.json"))}


def guardar_participante(persona: str, info: dict) -> None:
    DIR_PARTICIPANTES.mkdir(parents=True, exist_ok=True)
    (DIR_PARTICIPANTES / f"{persona}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2),
                                                        encoding="utf-8")


def borrar_toma(persona: str, sesion: str, nombre: str) -> None:
    """Borra el video (cualquier formato), los metadatos y los puntos de una toma."""
    carpeta = carpeta_sesion(persona, sesion)
    for ext in (*EXTENSIONES_VIDEO, ".json"):
        (carpeta / f"{nombre}{ext}").unlink(missing_ok=True)
    (carpeta_sesion(persona, sesion, DIR_PUNTOS) / f"{nombre}.npz").unlink(missing_ok=True)


def personas_prueba() -> set[str]:
    """Personas apartadas para la prueba final (protocolo/particion.json). Nunca se entrena con ellas."""
    ruta = DIR_PROTOCOLO / "particion.json"
    if not ruta.exists():
        return set()
    return set(json.loads(ruta.read_text(encoding="utf-8")).get("prueba", []))
