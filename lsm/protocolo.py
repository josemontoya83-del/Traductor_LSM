"""
Convierte protocolo/protocolo.json + vocabulario en la lista ordenada de TOMAS que graba una
persona en una sesión. Dentro de cada bloque y repetición el orden se baraja (con semilla fija
por persona/sesión) para que el cansancio no caiga siempre en las mismas señas.

La numeración de repeticiones continúa entre sesiones: si la sesión 1 tiene 3 repeticiones de
una seña, en la sesión 2 serán r04, r05, r06.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from .config import DIR_PROTOCOLO
from .datos import nombre_clip
from .vocabulario import Vocabulario, cargar as cargar_vocabulario, normalizar


@dataclass
class Toma:
    bloque: str
    nombre_bloque: str
    tipo: str            # letra | numero | sena | deletreo | negativo | respuesta
    etiqueta: str        # id de la letra / seña / palabra
    texto: str           # lo que se le muestra a la persona
    instruccion: str
    repeticion: int
    segundos_max: float
    parar_al_bajar: bool
    movimiento: bool = False
    modo: Optional[str] = None   # deletreo: "deletreo" o "numeros"
    pista: str = ""              # aclaración del significado (vocabulario)

    @property
    def nombre(self) -> str:
        return nombre_clip(self.tipo, self.etiqueta, self.repeticion)


@lru_cache(maxsize=1)
def cargar_protocolo() -> dict:
    return json.loads((DIR_PROTOCOLO / "protocolo.json").read_text(encoding="utf-8"))


def _elementos(fuente: str, sesion: str, prot: dict, vocab: Vocabulario) -> list[dict]:
    """-> [{etiqueta, texto, movimiento, modo}]"""
    if fuente == "letras":
        return [dict(etiqueta=l["id"], texto=l["texto"], movimiento=l["movimiento"]) for l in vocab.letras]
    if fuente == "numeros":
        return [dict(etiqueta=n["id"], texto=n["texto"], movimiento=n["movimiento"]) for n in vocab.numeros]
    if fuente.startswith("dominio:"):
        dominio = fuente.split(":", 1)[1]
        return [dict(etiqueta=s["id"], texto=s["texto"], pista=s.get("pista", ""))
                for s in vocab.dominios[dominio]["senas"]]
    if fuente == "deletreo":
        return [dict(etiqueta=normalizar(p), texto=p, modo="numeros" if p.isdigit() else "deletreo")
                for p in prot["deletreo"][sesion]]
    if fuente == "negativos":
        return [dict(etiqueta=n["id"], texto=n["texto"]) for n in prot["negativos"]]
    if fuente == "respuestas":
        return [dict(etiqueta=r["id"], texto=r["texto"]) for r in vocab.respuestas]
    raise ValueError(f"Fuente desconocida en el protocolo: {fuente}")


def _repeticiones_previas(prot: dict, sesion: str, bloque: dict) -> int:
    previas = 0
    for s in sorted(prot["sesiones"], key=int):
        if int(s) >= int(sesion):
            break
        for b in prot["sesiones"][s]:
            if b["tipo"] == bloque["tipo"] and b["fuente"] == bloque["fuente"]:
                previas += b["repeticiones"]
    return previas


def tomas(persona: str, sesion: str, bloques=None, incluir_opcionales: bool = False,
          prot: Optional[dict] = None, vocab: Optional[Vocabulario] = None) -> list[Toma]:
    prot = prot or cargar_protocolo()
    vocab = vocab or cargar_vocabulario()
    if sesion not in prot["sesiones"]:
        raise ValueError(f"La sesión '{sesion}' no existe en el protocolo ({list(prot['sesiones'])}).")
    salida = []
    for b in prot["sesiones"][sesion]:
        if bloques is not None and b["bloque"] not in bloques:
            continue
        if b.get("opcional") and not incluir_opcionales and bloques is None:
            continue
        elementos = _elementos(b["fuente"], sesion, prot, vocab)
        previas = _repeticiones_previas(prot, sesion, b)
        for r in range(b["repeticiones"]):
            orden = list(elementos)
            random.Random(f"{persona}-{sesion}-{b['bloque']}-{r}").shuffle(orden)
            for e in orden:
                instr_clave = "letra_movimiento" if (b["tipo"] == "letra" and e.get("movimiento")) else b["tipo"]
                salida.append(Toma(
                    bloque=b["bloque"], nombre_bloque=b["nombre"], tipo=b["tipo"], etiqueta=e["etiqueta"],
                    texto=e["texto"], instruccion=prot["instrucciones"][instr_clave], repeticion=previas + r + 1,
                    segundos_max=prot["segundos_maximos"][b["tipo"]],
                    parar_al_bajar=prot["parar_al_bajar_manos"][b["tipo"]],
                    movimiento=bool(e.get("movimiento")), modo=e.get("modo"), pista=e.get("pista", "")))
    return salida
