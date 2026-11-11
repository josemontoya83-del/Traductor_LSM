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
from collections import deque
from pathlib import Path
from typing import Optional, Protocol

import numpy as np

from .contrato import Candidato, ResultadoCamara

RAIZ = Path(__file__).resolve().parents[2]
MODELO_IA = RAIZ / "Modelo_ia"
DEBUG = os.getenv("LSM_DEBUG", "0") == "1"   # imprime cada segmento y guarda sus keypoints
DEBUG_DIR = RAIZ / "Pruebas" / "debug_segmentos"
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
    PRE_ROLL_S = 1.0          # margen de manos abajo que se guarda ANTES de la seña (luego se recorta)
    # En el dataset la seña ocupa ~70% de los 30 frames; el resto es reposo antes (~23-39% de la
    # duración de la seña) y después (~11-19%). Al cerrar, el segmento en vivo se recorta a esas
    # proporciones: si no, el pre-roll y la pausa de cierre "aplastan" la seña al remuestrear y el
    # modelo responde casi siempre "si". Valores elegidos reproduciendo el dataset por este motor
    # a 12-30 fps (93-94% vs 78-97% sin recorte).
    MARGEN_PREVIO = 0.39
    MARGEN_FINAL = 0.19
    MIN_ACTIVOS = 4           # frames con mano en posición de firmar; menos = ruido, se descarta

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
        self._flags: list[bool] = []  # True = frame en posición de firmar (paralelo a _segmento)
        self._pre: deque = deque()  # (t, vector) de los últimos PRE_ROLL_S antes de empezar la seña
        self._activos = 0
        self._t_inicio = 0.0
        self._t_ultima_activa = 0.0
        self._t_actual = 0.0
        self._id = 0
        self._dbg = {"t0": None, "frames": 0, "mano": 0, "hombros": 0, "activa": 0}

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
        self._t_actual = t
        if DEBUG:
            self._latido(vec, t)
        if self._activa(vec):
            if not self._segmento:
                self._t_inicio = t
                self._segmento = [v for (tt, v) in self._pre if t - tt <= self.PRE_ROLL_S]
                self._flags = [False] * len(self._segmento)
                self._pre.clear()
                self._activos = 0
            self._activos += 1
            self._segmento.append(vec)
            self._flags.append(True)
            self._t_ultima_activa = t
            if t - self._t_inicio > self.MAX_SEGMENTO_S:
                return self._cerrar()
            return ResultadoCamara(id=self._id, estado="firmando")
        if self._segmento:
            self._segmento.append(vec)  # se conservan los frames de la pausa corta
            self._flags.append(False)
            if t - self._t_ultima_activa >= self.PAUSA_CIERRE_S:
                return self._cerrar()
            return ResultadoCamara(id=self._id, estado="firmando")
        self._pre.append((t, vec))  # reposo: se guarda un margen previo por si empieza una seña
        while self._pre and t - self._pre[0][0] > self.PRE_ROLL_S:
            self._pre.popleft()
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

    def _latido(self, vec: np.ndarray, t: float) -> None:
        """Cada 3 s imprime fps y qué tanto se detectan manos/hombros (solo con LSM_DEBUG=1)."""
        d = self._dbg
        if d["t0"] is None:
            d["t0"] = t
        d["frames"] += 1
        d["mano"] += bool(vec[:126].any())
        d["hombros"] += bool(vec[126:].reshape(25, 4)[[11, 12], :2].any())
        d["activa"] += self._activa(vec)
        if t - d["t0"] >= 3.0:
            n = d["frames"]
            print(f"[LSM] {n / (t - d['t0']):4.1f} fps | mano {d['mano'] / n:4.0%} | hombros "
                  f"{d['hombros'] / n:4.0%} | en posicion de firmar {d['activa'] / n:4.0%}", flush=True)
            self._dbg = {"t0": t, "frames": 0, "mano": 0, "hombros": 0, "activa": 0}

    def _recortar(self, segmento: list, flags: list) -> list:
        """Deja la seña con los mismos márgenes de reposo (antes/después) que trae el dataset."""
        idx = [i for i, f in enumerate(flags) if f]
        if not idx:
            return segmento
        ini, fin = idx[0], idx[-1]
        largo = fin - ini + 1
        desde = max(0, ini - round(self.MARGEN_PREVIO * largo))
        hasta = min(len(segmento), fin + 1 + round(self.MARGEN_FINAL * largo))
        return segmento[desde:hasta]

    def _cerrar(self) -> ResultadoCamara:
        segmento, self._segmento = self._segmento, []
        flags, self._flags = self._flags, []
        segmento = self._recortar(segmento, flags)
        dur = self._t_actual - self._t_inicio
        if len(segmento) < self.MIN_FRAMES or self._activos < self.MIN_ACTIVOS:
            if DEBUG:
                print(f"[LSM] segmento DESCARTADO: {len(segmento)} frames (min {self.MIN_FRAMES}), "
                      f"{self._activos} activos (min {self.MIN_ACTIVOS}), {dur:.1f}s", flush=True)
            return ResultadoCamara(id=self._id, estado="reposo")
        seq = self._normalizar(self._remuestrear(segmento))
        prob = self._modelo.predict(seq[None], verbose=0)[0]
        orden = np.argsort(-prob)[:3]
        top3 = [Candidato(palabra=self._clases[i], prob=round(float(prob[i]), 3)) for i in orden]
        if DEBUG:
            top = ", ".join(f"{c.palabra} {c.prob:.0%}" for c in top3)
            print(f"[LSM] segmento: {len(segmento)} frames, {self._activos} activos, {dur:.1f}s "
                  f"-> {top}", flush=True)
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            np.save(DEBUG_DIR / f"{time.strftime('%H%M%S')}_{self._id + 1:03d}_{top3[0].palabra}.npy",
                    np.array(segmento, dtype=np.float32))
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