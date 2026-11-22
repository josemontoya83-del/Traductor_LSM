"""
Deletreo: de "probabilidades de letra por cuadro" a texto, y de texto a palabra del vocabulario.

DecodificadorLetras (cuadro a cuadro):
  - suaviza las probabilidades de los últimos cuadros;
  - una letra se "escribe" cuando se mantiene estable ESTABLE cuadros seguidos con confianza;
  - la misma letra dos veces seguidas (p. ej. la doble C de "acción") se escribe solo si hubo
    una pausa o transición entre ambas.

buscar_en_lexico(): compara lo deletreado contra el vocabulario con distancia de edición,
así "KARDES" se corrige a "Kárdex". Si nada se parece, se respeta lo deletreado (nombres).
"""
from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

from .vocabulario import NADA, normalizar


class DecodificadorLetras:
    UMBRAL = 0.55     # confianza mínima de la letra suavizada
    ESTABLE = 3       # cuadros seguidos con la misma letra para escribirla
    SUAVIZADO = 3     # cuadros que se promedian

    def __init__(self, clases: list[str], permitidas: Optional[set] = None) -> None:
        self.clases = list(clases)
        self.i_nada = self.clases.index(NADA) if NADA in self.clases else None
        self.mascara = np.ones(len(self.clases), np.float32)
        self.permitir(permitidas)
        self.reiniciar()

    def permitir(self, permitidas: Optional[set]) -> None:
        """Limita a un conjunto (p. ej. solo letras o solo números). None = todas."""
        if permitidas is None:
            self.mascara[:] = 1
        else:
            self.mascara = np.array([1.0 if (c in permitidas or c == NADA) else 0.0
                                     for c in self.clases], np.float32)

    def reiniciar(self) -> None:
        self._hist: deque = deque(maxlen=self.SUAVIZADO)
        self._actual: Optional[int] = None
        self._cuenta = 0
        self._ultima: Optional[int] = None
        self._hubo_pausa = True
        self.letras: list[str] = []

    @property
    def texto(self) -> str:
        return "".join(self.letras).upper()

    def empujar(self, prob: np.ndarray) -> Optional[str]:
        """Probabilidades de un cuadro -> letra recién escrita (o None)."""
        p = np.asarray(prob, np.float32) * self.mascara
        p = p / max(float(p.sum()), 1e-9)
        self._hist.append(p)
        media = np.mean(self._hist, axis=0)
        mejor = int(media.argmax())
        if media[mejor] < self.UMBRAL:
            mejor = self.i_nada if self.i_nada is not None else -1
        if mejor == self._actual:
            self._cuenta += 1
        else:
            self._actual, self._cuenta = mejor, 1
        if self._cuenta != self.ESTABLE:
            return None
        if mejor == -1 or mejor == self.i_nada:
            self._hubo_pausa = True
            return None
        if mejor == self._ultima and not self._hubo_pausa:
            return None
        self._ultima, self._hubo_pausa = mejor, False
        self.letras.append(self.clases[mejor])
        return self.clases[mejor]

    def terminar(self) -> str:
        texto = self.texto
        self.reiniciar()
        return texto


def levenshtein(a: str, b: str) -> int:
    previa = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        actual = [i]
        for j, y in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (x != y)))
        previa = actual
    return previa[-1]


def buscar_en_lexico(texto: str, lexico: dict[str, str], n: int = 3) -> list[tuple[str, float]]:
    """-> [(palabra como se muestra, parecido 0-1)] de mayor a menor parecido."""
    q = normalizar(texto)
    if not q:
        return []
    puntajes = []
    for norm, mostrar in lexico.items():
        d = levenshtein(q, norm)
        puntajes.append((mostrar, 1 - d / max(len(q), len(norm))))
    puntajes.sort(key=lambda x: -x[1])
    return puntajes[:n]
