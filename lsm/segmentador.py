"""
Segmentador: decide cuándo empieza y termina una seña (o una palabra deletreada).

Regla (la misma para la captura, el entrenamiento y el servidor en vivo):
  - "activo" = hay una mano levantada (muñeca a menos de UMBRAL_REPOSO anchos de hombro por
    debajo de los hombros).
  - Empieza al primer cuadro activo. Termina cuando las manos llevan PAUSA_CIERRE s abajo/ausentes.
  - El segmento incluye MARGEN s de reposo antes del primer cuadro activo y después del último.

Antes, la captura cortaba con ESPACIO y el servidor cortaba con esta regla: las señas quedaban
distintas y había que parchar márgenes a mano. Ahora el entrenamiento corta los videos con este
mismo código, así que lo que ve el modelo al entrenar es lo que ve en vivo.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import puntos as P
from .rasgos import ReferenciaHombros, mano_activa


@dataclass
class Evento:
    tipo: str                      # "reposo" | "firmando" | "cierre" | "descartado"
    activa: bool = False           # el cuadro actual tiene una mano levantada
    ref: Optional[tuple] = None    # referencia de hombros vigente
    cuadros: list = field(default_factory=list)   # solo en "cierre": cuadros del segmento
    tiempos: list = field(default_factory=list)
    ini: int = -1                  # solo en "cierre": índices [ini, fin) en el flujo
    fin: int = -1

    def clip(self) -> dict:
        return P.apilar(self.cuadros, self.tiempos)


class Segmentador:
    PAUSA_CIERRE = 0.5   # s con manos abajo para dar por terminada la seña
    MARGEN = 0.25        # s de reposo que se conservan antes y después
    MIN_ACTIVOS = 3      # cuadros activos mínimos; menos = ruido
    MIN_DURACION = 0.2   # s entre el primer y el último cuadro activo

    def __init__(self, max_duracion: float = 8.0) -> None:
        self.max_duracion = max_duracion
        self.reiniciar()

    def reiniciar(self) -> None:
        self._ref = ReferenciaHombros()
        self._pre: deque = deque()          # (n, t, cuadro) de reposo reciente
        self._seg: list = []                # (n, t, cuadro, activo)
        self._n = 0
        self._t_primera = self._t_ultima = 0.0
        self._activos = 0

    @property
    def en_segmento(self) -> bool:
        return bool(self._seg)

    def empujar(self, t: float, cuadro: dict) -> Evento:
        n = self._n
        self._n += 1
        ref = self._ref.empujar(cuadro["pose"])
        activa = bool(mano_activa(cuadro["mano_der"], ref) or mano_activa(cuadro["mano_izq"], ref))

        if activa:
            if not self._seg:
                self._seg = [(nn, tt, cc, False) for nn, tt, cc in self._pre if t - tt <= self.MARGEN]
                self._pre.clear()
                self._t_primera, self._activos = t, 0
            self._seg.append((n, t, cuadro, True))
            self._activos += 1
            self._t_ultima = t
            if t - self._t_primera >= self.max_duracion:
                return self._cerrar(ref, activa)
            return Evento("firmando", activa, ref)

        if self._seg:
            self._seg.append((n, t, cuadro, False))
            if t - self._t_ultima >= self.PAUSA_CIERRE:
                return self._cerrar(ref, activa)
            return Evento("firmando", activa, ref)

        self._pre.append((n, t, cuadro))
        while self._pre and t - self._pre[0][1] > self.MARGEN:
            self._pre.popleft()
        return Evento("reposo", activa, ref)

    def terminar(self) -> Optional[Evento]:
        """Fin del flujo (fin de un video): cierra el segmento abierto, si hay."""
        return self._cerrar(None, False) if self._seg else None

    def _cerrar(self, ref, activa) -> Evento:
        seg, self._seg = self._seg, []
        seg = [s for s in seg if s[1] <= self._t_ultima + self.MARGEN]
        if self._activos < self.MIN_ACTIVOS or self._t_ultima - self._t_primera < self.MIN_DURACION:
            return Evento("descartado", activa, ref)
        return Evento("cierre", activa, ref, cuadros=[s[2] for s in seg], tiempos=[s[1] for s in seg],
                      ini=seg[0][0], fin=seg[-1][0] + 1)


def segmentar_clip(clip: dict, max_duracion: float = 8.0) -> list[Evento]:
    """Pasa un clip grabado por el segmentador (igual que en vivo) y devuelve los segmentos."""
    seg = Segmentador(max_duracion)
    eventos = []
    for i, t in enumerate(clip["t"]):
        ev = seg.empujar(float(t), P.cuadro(clip, i))
        if ev.tipo == "cierre":
            eventos.append(ev)
    ev = seg.terminar()
    if ev is not None and ev.tipo == "cierre":
        eventos.append(ev)
    return eventos


def segmento_principal(clip: dict, max_duracion: float = 8.0) -> Optional[Evento]:
    """El segmento más largo del clip (la seña grabada), o None si no hubo ninguna."""
    eventos = segmentar_clip(clip, max_duracion)
    return max(eventos, key=lambda e: e.tiempos[-1] - e.tiempos[0]) if eventos else None


def activos_por_cuadro(clip: dict) -> np.ndarray:
    """(T,) True donde hay una mano levantada, con la referencia en flujo (igual que en vivo)."""
    ref = ReferenciaHombros()
    salida = np.zeros(len(clip["t"]), bool)
    for i in range(len(salida)):
        r = ref.empujar(clip["pose"][i])
        salida[i] = bool(mano_activa(clip["mano_der"][i], r) or mano_activa(clip["mano_izq"][i], r))
    return salida
