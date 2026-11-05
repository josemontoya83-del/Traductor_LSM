"""Contrato de mensajes entre Frontend y Backend de LSM-Connect (ver Backend/README.md)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Estado = Literal["reposo", "firmando", "palabra", "duda"]
Rol = Literal["estudiante", "ventanilla"]


class Candidato(BaseModel):
    palabra: str
    prob: float


class ResultadoCamara(BaseModel):
    """Respuesta del backend por cada frame recibido en /ws/camara."""
    id: int = 0                       # sube en 1 con cada evento (palabra/duda); sirve para no repetirlo
    estado: Estado = "reposo"
    palabra: Optional[str] = None     # solo en estado "palabra"
    confianza: float = 0.0
    top3: list[Candidato] = Field(default_factory=list)  # en "palabra" y "duda"


class MensajeChat(BaseModel):
    tipo: Literal["mensaje"] = "mensaje"
    rol: Rol
    texto: str
    hora: str                          # ISO 8601
