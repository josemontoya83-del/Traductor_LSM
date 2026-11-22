"""
Revisión en vivo de una imagen: ¿se ve bien a la persona? ¿tiene una mano levantada?
La usan el programa de captura clásico y la grabación en el navegador (Backend /ws/revision),
con la MISMA regla de "mano levantada" que el segmentador.
"""
from __future__ import annotations

import numpy as np

from . import puntos as P
from .rasgos import ReferenciaHombros, mano_activa

MENSAJES_ENCUADRE = {
    "ok": "Encuadre correcto",
    "sin_persona": "No se ven los hombros: colócate de frente a la cámara",
    "lejos": "Estás lejos: acércate un poco",
    "cerca": "Estás muy cerca: aléjate un poco",
    "cabeza": "Se corta la cabeza: baja la cámara o aléjate",
}


def encuadre(cuadro: dict) -> str:
    """Código de encuadre: ok | sin_persona | lejos | cerca | cabeza."""
    if not P.hay_hombros(cuadro):
        return "sin_persona"
    ancho = float(np.linalg.norm(cuadro["pose"][11, :2] - cuadro["pose"][12, :2]))
    if ancho < 0.16:
        return "lejos"
    if ancho > 0.42:
        return "cerca"
    if cuadro["pose"][0, 1] < 0.03:
        return "cabeza"
    return "ok"


class Revisor:
    """Estado cuadro a cuadro de una conexión (la referencia de hombros se suaviza en el tiempo)."""

    def __init__(self) -> None:
        self._ref = ReferenciaHombros()

    def revisar(self, cuadro: dict) -> dict:
        ref = self._ref.empujar(cuadro["pose"])
        activa = bool(mano_activa(cuadro["mano_der"], ref) or mano_activa(cuadro["mano_izq"], ref))
        return {"encuadre": encuadre(cuadro), "hombros": P.hay_hombros(cuadro),
                "mano": P.hay_mano(cuadro), "activa": activa}
