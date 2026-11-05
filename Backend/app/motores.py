"""
Motores de reconocimiento. El front no sabe cuál se usa: ambos devuelven ResultadoCamara.

  MotorSimulado -> predicciones falsas con un ciclo fijo (para desarrollar el front ya).
  MotorReal     -> MediaPipe + modelo entrenado (Modelo_ia/lsm_tramites.h5).

Segmentación del MotorReal (igual que como se grabó el dataset: una seña = un segmento):
  manos activas -> "firmando"; manos abajo/ausentes un rato -> se cierra el segmento,
  se remuestrea a 30 frames, se normaliza (preprocesar.py) y se clasifica.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Protocol

import numpy as np

from .contrato import Candidato, ResultadoCamara

RAIZ = Path(__file__).resolve().parents[2]
MODELO_IA = RAIZ / "Modelo_ia"
CLASES_DEFECTO = ["inscripcion", "reinscripcion", "kardex", "constancia", "foto", "credencial",
                  "documentos", "solicitar", "recoger", "entrega", "si", "no", "duda", "gracias"]


class Motor(Protocol):
    nombre: str

    def procesar_frame(self, jpeg: bytes) -> ResultadoCamara: ...
    def reiniciar(self) -> None: ...


class MotorSimulado:
    """Ciclo de 60 frames: reposo -> firmando -> palabra (o duda cada 4 ciclos) -> reposo."""
    nombre = "simulado"

    def __init__(self) -> None:
        self.reiniciar()

    def reiniciar(self) -> None:
        self._n, self._ciclo, self._id = 0, 0, 0

    def procesar_frame(self, jpeg: bytes) -> ResultadoCamara:
        pos = self._n % 60
        self._n += 1
        if pos < 10 or pos > 30:
            if pos == 59:
                self._ciclo += 1
            return ResultadoCamara(id=self._id, estado="reposo")
        if pos < 30:
            return ResultadoCamara(id=self._id, estado="firmando")
        palabra = CLASES_DEFECTO[self._ciclo % len(CLASES_DEFECTO)]
        otras = [c for c in CLASES_DEFECTO if c != palabra][:2]
        self._id += 1
        if self._ciclo % 4 == 3:  # simula que duda
            top3 = [Candidato(palabra=palabra, prob=0.46), Candidato(palabra=otras[0], prob=0.31),
                    Candidato(palabra=otras[1], prob=0.12)]
            return ResultadoCamara(id=self._id, estado="duda", confianza=0.46, top3=top3)
        top3 = [Candidato(palabra=palabra, prob=0.93), Candidato(palabra=otras[0], prob=0.04),
                Candidato(palabra=otras[1], prob=0.02)]
        return ResultadoCamara(id=self._id, estado="palabra", palabra=palabra, confianza=0.93, top3=top3)


# ---------------------------------------------------------------- motor real
_MODELO = None
_CLASES: list[str] = []


def _cargar_modelo():
    """Carga el modelo una sola vez y lo comparte entre conexiones."""
    global _MODELO, _CLASES
    if _MODELO is None:
        sys.path.insert(0, str(MODELO_IA))  # para importar preprocesar y captura_dataset_tramites
        import tf_keras as keras

        ruta = MODELO_IA / "lsm_tramites.h5"
        if not ruta.exists():
            raise FileNotFoundError(
                f"No existe {ruta}. Genera el modelo con: python Modelo_ia\\entrenar_modelo.py --guardar")
        _MODELO = keras.models.load_model(ruta)
        _CLASES = json.loads((MODELO_IA / "clases_tramites.json").read_text(encoding="utf-8"))
    return _MODELO, _CLASES


class MotorReal:
    nombre = "real"
    UMBRAL_CONFIANZA = float(os.getenv("LSM_UMBRAL", "0.70"))  # debajo de esto -> "duda"
    PAUSA_CIERRE_S = 0.5      # manos abajo/ausentes este tiempo = terminó la seña
    MIN_FRAMES = 10           # igual que al grabar el dataset
    MAX_SEGMENTO_S = 6.0      # corte de seguridad

    def __init__(self) -> None:
        import mediapipe as mp

        self._modelo, self._clases = _cargar_modelo()
        from captura_dataset_tramites import extraer_keypoints_msl150, remuestrear
        from preprocesar import UMBRAL_REPOSO, normalizar_secuencia

        self._extraer, self._remuestrear = extraer_keypoints_msl150, remuestrear
        self._normalizar, self._umbral_reposo = normalizar_secuencia, UMBRAL_REPOSO
        # mismos parámetros con los que se grabó el dataset
        self._holistic = mp.solutions.holistic.Holistic(min_detection_confidence=0.85,
                                                        min_tracking_confidence=0.25)
        self.reiniciar()

    def reiniciar(self) -> None:
        self._segmento: list[np.ndarray] = []
        self._t_inicio = 0.0
        self._t_ultima_activa = 0.0
        self._id = 0

    # -- entrada por imagen (el video solo pasa por RAM, nunca se guarda)
    def procesar_frame(self, jpeg: bytes) -> ResultadoCamara:
        import cv2

        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return ResultadoCamara(id=self._id, estado="reposo")
        resultados = self._holistic.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        return self.procesar_vector(self._extraer(resultados))

    # -- entrada por keypoints (226 valores); aquí vive la lógica, es lo que se prueba
    def procesar_vector(self, vec: np.ndarray, t: Optional[float] = None) -> ResultadoCamara:
        t = time.monotonic() if t is None else t
        if self._activa(vec):
            if not self._segmento:
                self._t_inicio = t
            self._segmento.append(vec)
            self._t_ultima_activa = t
            if t - self._t_inicio > self.MAX_SEGMENTO_S:
                return self._cerrar()
            return ResultadoCamara(id=self._id, estado="firmando")
        if self._segmento:
            self._segmento.append(vec)  # se conservan los frames de la pausa corta
            if t - self._t_ultima_activa >= self.PAUSA_CIERRE_S:
                return self._cerrar()
            return ResultadoCamara(id=self._id, estado="firmando")
        return ResultadoCamara(id=self._id, estado="reposo")

    def _activa(self, v: np.ndarray) -> bool:
        """Hay una mano en posición de firmar (no colgando en reposo)."""
        hombros = v[126:].reshape(25, 4)[[11, 12], :2]
        if not hombros.any():
            return bool(v[:126].any())
        centro_y = hombros[:, 1].mean()
        ancho = np.linalg.norm(hombros[0] - hombros[1]) + 1e-6
        for ini in (0, 63):
            mano = v[ini:ini + 63].reshape(21, 3)
            if mano.any() and (mano[0, 1] - centro_y) / ancho <= self._umbral_reposo:
                return True
        return False

    def _cerrar(self) -> ResultadoCamara:
        segmento, self._segmento = self._segmento, []
        if len(segmento) < self.MIN_FRAMES:
            return ResultadoCamara(id=self._id, estado="reposo")
        seq = self._normalizar(self._remuestrear(segmento))
        prob = self._modelo.predict(seq[None], verbose=0)[0]
        orden = np.argsort(-prob)[:3]
        top3 = [Candidato(palabra=self._clases[i], prob=round(float(prob[i]), 3)) for i in orden]
        self._id += 1
        mejor = top3[0]
        if mejor.palabra == "reposo":
            return ResultadoCamara(id=self._id - 1, estado="reposo")
        if mejor.prob >= self.UMBRAL_CONFIANZA:
            return ResultadoCamara(id=self._id, estado="palabra", palabra=mejor.palabra,
                                   confianza=mejor.prob, top3=top3)
        return ResultadoCamara(id=self._id, estado="duda", confianza=mejor.prob, top3=top3)


def crear_motor() -> Motor:
    """LSM_MOTOR=simulado (defecto) | real"""
    return MotorReal() if os.getenv("LSM_MOTOR", "simulado").lower() == "real" else MotorSimulado()
