"""
Vocabulario por capas:
  - vocabulario/letras.json          alfabeto + números (deletreo: sirve para CUALQUIER palabra)
  - vocabulario/dominios/general.json  señas que sirven en cualquier ventanilla (siempre activas)
  - vocabulario/dominios/<x>.json      paquete de un lugar (escolar, biblioteca, caja...)
  - vocabulario/respuestas.json      respuestas rápidas del empleado

Para llevar el sistema a otro lugar: se crea vocabulario/dominios/<nuevo>.json, se graban sus
señas con el protocolo y se reentrena. El deletreo funciona desde el primer día con su "lexico".
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from .config import DIR_VOCABULARIO

DOMINIO_BASE = "general"
NADA = "_nada"   # clase "no es seña / no es letra" (movimientos sin significado, transiciones)


def _leer(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


@dataclass
class Vocabulario:
    letras: list[dict]
    numeros: list[dict]
    dominios: dict[str, dict]                 # id -> contenido del json
    respuestas: list[dict] = field(default_factory=list)

    # ---- señas
    def senas(self, dominios=None) -> list[dict]:
        """Señas de 'general' + los dominios pedidos (None = todos). Cada una con su 'dominio'."""
        activos = self.dominios_activos(dominios)
        return [dict(s, dominio=d) for d in activos for s in self.dominios[d]["senas"]]

    def dominios_activos(self, dominios=None) -> list[str]:
        if dominios is None:
            return list(self.dominios)
        pedidos = [d for d in dominios if d in self.dominios and d != DOMINIO_BASE]
        return [DOMINIO_BASE, *pedidos] if DOMINIO_BASE in self.dominios else pedidos

    def texto(self, id_: str) -> str:
        for d in self.dominios.values():
            for s in d["senas"]:
                if s["id"] == id_:
                    return s["texto"]
        for l in self.letras + self.numeros:
            if l["id"] == id_:
                return l["texto"]
        return id_

    # ---- deletreo
    def lexico(self, dominios=None) -> dict[str, str]:
        """Palabras contra las que se compara lo deletreado: normalizado -> como se muestra."""
        salida = {}
        for d in self.dominios_activos(dominios):
            contenido = self.dominios[d]
            textos = [s["texto"] for s in contenido["senas"]] + list(contenido.get("lexico", []))
            for t in textos:
                for parte in t.replace("¿", "").replace("?", "").split("/"):
                    n = normalizar(parte)
                    if n:
                        salida.setdefault(n, parte.strip())
        return salida

    def respuestas_de(self, dominios=None) -> list[dict]:
        activos = set(self.dominios_activos(dominios))
        return [r for r in self.respuestas if r.get("dominio", DOMINIO_BASE) in activos]


@lru_cache(maxsize=1)
def cargar() -> Vocabulario:
    letras = _leer(DIR_VOCABULARIO / "letras.json")
    dominios = {}
    for ruta in sorted((DIR_VOCABULARIO / "dominios").glob("*.json")):
        contenido = _leer(ruta)
        dominios[contenido["dominio"]] = contenido
    if DOMINIO_BASE in dominios:  # 'general' siempre primero
        dominios = {DOMINIO_BASE: dominios.pop(DOMINIO_BASE), **dominios}
    ruta_r = DIR_VOCABULARIO / "respuestas.json"
    respuestas = _leer(ruta_r)["respuestas"] if ruta_r.exists() else []
    return Vocabulario(letras["letras"], letras["numeros"], dominios, respuestas)


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos (la ñ se conserva) y solo letras/dígitos."""
    texto = texto.lower().replace("ñ", "\0")
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return "".join(c for c in texto.replace("\0", "ñ") if c.isalnum())
