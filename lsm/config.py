"""Rutas del proyecto. La carpeta de datos se puede mover (p. ej. a un disco externo) con la
variable de entorno LSM_DATOS (y la de modelos con LSM_MODELOS)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR_DATOS = Path(os.getenv("LSM_DATOS", RAIZ / "datos"))
DIR_VIDEOS = DIR_DATOS / "videos"        # videos/P01/s1/<clip>.mp4 + <clip>.json (metadatos)
DIR_PUNTOS = DIR_DATOS / "puntos"        # puntos/P01/s1/<clip>.npz (sale de extraer_puntos)
ARCHIVO_PARTICIPANTES = DIR_DATOS / "participantes.json"
DIR_VOCABULARIO = RAIZ / "vocabulario"
DIR_PROTOCOLO = RAIZ / "protocolo"
DIR_MODELOS = Path(os.getenv("LSM_MODELOS", RAIZ / "modelos"))
