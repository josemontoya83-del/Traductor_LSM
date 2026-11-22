"""Contrato de mensajes entre Frontend y Backend de LSM-Connect (ver Backend/README.md)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Estado = Literal["reposo", "firmando", "letra", "palabra", "duda"]
Modo = Literal["senas", "deletreo", "numeros"]


class Candidato(BaseModel):
    palabra: str
    prob: float


class ResultadoCamara(BaseModel):
    """Respuesta del backend por cada imagen recibida en /ws/camara."""
    id: int = 0                       # sube en 1 con cada palabra/duda; procesar cada id una sola vez
    estado: Estado = "reposo"
    palabra: Optional[str] = None     # solo en "palabra": texto listo para mostrar
    confianza: float = 0.0
    top3: list[Candidato] = Field(default_factory=list)  # en "palabra" y "duda"
    parcial: str = ""                 # deletreo en curso ("KAR")
    aviso: Optional[str] = None       # mensaje para la persona (p. ej. falta un modelo)


class ConfigCamara(BaseModel):
    """Front -> backend (texto): {"tipo": "config", "modo": "deletreo", "dominios": ["escolar"]}"""
    tipo: Literal["config"] = "config"
    modo: Modo = "senas"
    dominios: list[str] = Field(default_factory=list)
