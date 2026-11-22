"""
Motor de reconocimiento en vivo. No depende de FastAPI: el Backend solo lo envuelve.

Modos:
  "senas"     una seña completa -> palabra (modelo de señas, filtrado por dominios activos)
  "deletreo"  letra por letra -> texto -> se busca en el vocabulario (modelo de letras)
  "numeros"   igual que deletreo pero solo dígitos (matrícula, teléfono...)

Flujo por cuadro: imagen -> puntos (lsm.puntos) -> segmentador (lsm.segmentador) ->
  señas:    al cerrar el segmento, rasgos de seña -> modelo -> palabra / duda
  deletreo: en cada cuadro, ventana de letra -> modelo -> decodificador -> letra parcial;
            al bajar la mano, el texto se compara con el vocabulario -> palabra / duda
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np

from . import modelos, puntos as P
from .config import DIR_MODELOS
from .decodificador import DecodificadorLetras, buscar_en_lexico
from .rasgos import SelectorMano, VentanaLetras, rasgos_letra, secuencia_sena
from .segmentador import Segmentador
from .vocabulario import NADA, Vocabulario, cargar as cargar_vocabulario

MODOS = ("senas", "deletreo", "numeros")
MAX_DURACION = {"senas": 8.0, "deletreo": 20.0, "numeros": 20.0}


@dataclass
class Resultado:
    id: int = 0                       # sube con cada palabra/duda; el front procesa cada id una vez
    estado: str = "reposo"            # reposo | firmando | letra | palabra | duda
    palabra: Optional[str] = None     # texto listo para mostrar (en "palabra")
    confianza: float = 0.0
    top3: list = field(default_factory=list)   # [{"palabra", "prob"}] en "palabra" y "duda"
    parcial: str = ""                 # deletreo en curso, p. ej. "KAR"
    aviso: Optional[str] = None       # problema que el front debe mostrar (falta un modelo...)

    def a_dict(self) -> dict:
        return asdict(self)


def _cand(palabra: str, prob: float) -> dict:
    return {"palabra": palabra, "prob": round(float(prob), 3)}


class MotorLSM:
    UMBRAL_SENA = 0.70      # debajo -> "duda" con 3 opciones
    UMBRAL_LEXICO = 0.70    # parecido mínimo para sugerir una palabra del vocabulario

    def __init__(self, vocab: Optional[Vocabulario] = None, carpeta_modelos=DIR_MODELOS,
                 base: Optional["MotorLSM"] = None) -> None:
        """base: otro motor del que se reutilizan vocabulario y modelos ya cargados (el servidor
        crea un motor por conexión, pero carga los modelos una sola vez)."""
        if base is not None:
            self.vocab = base.vocab
            self.m_senas, self.meta_senas = base.m_senas, base.meta_senas
            self.m_letras, self.meta_letras = base.m_letras, base.meta_letras
        else:
            self.vocab = vocab or cargar_vocabulario()
            self.m_senas = self.m_letras = None
            self.meta_senas = self.meta_letras = None
            if modelos.existe("senas", carpeta_modelos):
                self.m_senas, self.meta_senas = modelos.cargar("senas", carpeta_modelos)
            if modelos.existe("letras", carpeta_modelos):
                self.m_letras, self.meta_letras = modelos.cargar("letras", carpeta_modelos)
        if self.m_senas is None and self.m_letras is None:
            raise FileNotFoundError("No hay modelos en 'modelos/'. Entrena primero "
                                    "(herramientas/entrenar_senas.py y entrenar_letras.py).")
        self._holistic = None
        self._id = 0
        self.decod = DecodificadorLetras(self.meta_letras["clases"]) if self.meta_letras else None
        self.configurar("senas", [])

    # ------------------------------------------------------------ configuración
    def configurar(self, modo: str, dominios: list[str]) -> None:
        self.modo = modo if modo in MODOS else "senas"
        self.dominios = self.vocab.dominios_activos(dominios)
        if self.meta_senas:
            clases = self.meta_senas["clases"]
            permitidas = {s["id"] for s in self.vocab.senas(self.dominios)}
            self._mascara_senas = np.array([1.0 if (c in permitidas or c == NADA) else 0.0
                                            for c in clases], np.float32)
        if self.decod:
            ids = self.vocab.numeros if self.modo == "numeros" else self.vocab.letras
            self.decod.permitir({x["id"] for x in ids})
        self._lexico = self.vocab.lexico(self.dominios)
        self.reiniciar()

    def reiniciar(self) -> None:
        self.seg = Segmentador(MAX_DURACION[self.modo])
        self.ventana = VentanaLetras()
        self.selector = SelectorMano()
        if self.decod:
            self.decod.reiniciar()

    def cerrar(self) -> None:
        if self._holistic is not None:
            self._holistic.close()
            self._holistic = None

    # ------------------------------------------------------------ entrada
    def procesar_imagen(self, bgr: np.ndarray) -> Resultado:
        """Imagen BGR (OpenCV). El video solo pasa por memoria: nunca se guarda."""
        if self._holistic is None:
            self._holistic = P.crear_holistic()
        return self.procesar_cuadro(P.procesar_imagen(self._holistic, bgr), time.monotonic())

    def procesar_cuadro(self, cuadro: dict, t: float) -> Resultado:
        ev = self.seg.empujar(t, cuadro)
        if self.modo == "senas":
            return self._paso_senas(ev)
        return self._paso_deletreo(ev, cuadro, t)

    def terminar(self) -> Optional[Resultado]:
        """Cierra el segmento abierto (fin de un video en la evaluación)."""
        ev = self.seg.terminar()
        if ev is None:
            return None
        if self.modo == "senas":
            return self._clasificar_sena(ev.clip()) if ev.tipo == "cierre" and self.m_senas else None
        return self._resolver_texto(self.decod.terminar()) if self.decod else None

    # ------------------------------------------------------------ señas
    def _paso_senas(self, ev) -> Resultado:
        if self.m_senas is None:
            return Resultado(self._id, aviso="Todavía no hay modelo de señas entrenado. Usa el deletreo.")
        if ev.tipo == "cierre":
            return self._clasificar_sena(ev.clip())
        return Resultado(self._id, "firmando" if ev.tipo == "firmando" else "reposo")

    def _clasificar_sena(self, clip: dict) -> Resultado:
        x, _ = secuencia_sena(clip)
        prob = self.m_senas(x[None], training=False).numpy()[0] * self._mascara_senas
        prob = prob / max(float(prob.sum()), 1e-9)
        clases = self.meta_senas["clases"]
        orden = [i for i in np.argsort(-prob) if clases[i] != NADA][:3]
        if clases[int(prob.argmax())] == NADA:
            return Resultado(self._id, "reposo")
        self._id += 1
        top3 = [_cand(self.vocab.texto(clases[i]), prob[i]) for i in orden]
        mejor = top3[0]
        if mejor["prob"] >= self.UMBRAL_SENA:
            return Resultado(self._id, "palabra", mejor["palabra"], mejor["prob"], top3)
        return Resultado(self._id, "duda", None, mejor["prob"], top3)

    # ------------------------------------------------------------ deletreo
    def _paso_deletreo(self, ev, cuadro: dict, t: float) -> Resultado:
        if self.m_letras is None:
            return Resultado(self._id, aviso="Todavía no hay modelo de letras entrenado. Usa las señas.")
        # La ventana se alimenta SIEMPRE (también en reposo), igual que al entrenar.
        ventana = self.ventana.empujar(t, rasgos_letra(self.selector.canonico(cuadro, ev.ref), ev.ref))
        if ev.tipo == "firmando" and ev.activa:
            prob = self.m_letras(ventana[None], training=False).numpy()[0]
            self.decod.empujar(prob)
        if ev.tipo in ("cierre", "descartado"):
            return self._resolver_texto(self.decod.terminar())
        if ev.tipo == "firmando":
            return Resultado(self._id, "letra" if self.decod.texto else "firmando", parcial=self.decod.texto)
        return Resultado(self._id, "reposo")

    def _resolver_texto(self, texto: str) -> Resultado:
        if not texto:
            return Resultado(self._id, "reposo")
        self._id += 1
        if self.modo == "numeros":
            return Resultado(self._id, "palabra", texto, 1.0, [_cand(texto, 1.0)])
        tal_cual = texto.capitalize()
        cands = buscar_en_lexico(texto, self._lexico)
        if cands and cands[0][1] >= 0.999:          # coincide exacto con el vocabulario
            return Resultado(self._id, "palabra", cands[0][0], 1.0, [_cand(*c) for c in cands])
        if cands and cands[0][1] >= self.UMBRAL_LEXICO:  # se parece: que la persona confirme
            top3 = [_cand(*c) for c in cands[:2]] + [_cand(tal_cual, 0.0)]
            return Resultado(self._id, "duda", None, cands[0][1], top3)
        # No se parece a nada del vocabulario (p. ej. un nombre): se respeta lo deletreado.
        return Resultado(self._id, "palabra", tal_cual, 1.0, [_cand(tal_cual, 1.0)] + [_cand(*c) for c in cands[:2]])


class MotorSimulado:
    """Predicciones falsas con un ciclo fijo, para trabajar la interfaz sin modelos."""

    def __init__(self, vocab: Optional[Vocabulario] = None) -> None:
        self.vocab = vocab or cargar_vocabulario()
        self._id = 0
        self.configurar("senas", [])

    def configurar(self, modo: str, dominios: list[str]) -> None:
        self.modo = modo if modo in MODOS else "senas"
        self.dominios = self.vocab.dominios_activos(dominios)
        self._palabras = [s["texto"] for s in self.vocab.senas(self.dominios)]
        self.reiniciar()

    def reiniciar(self) -> None:
        self._n, self._ciclo = 0, 0

    def cerrar(self) -> None:
        pass

    def procesar_imagen(self, bgr=None) -> Resultado:
        return self.procesar_cuadro(None, 0.0)

    def procesar_cuadro(self, cuadro, t) -> Resultado:
        pos = self._n % 60
        self._n += 1
        if pos == 59:
            self._ciclo += 1
        if self.modo == "senas":
            if pos < 10 or pos > 30:
                return Resultado(self._id, "reposo")
            if pos < 30:
                return Resultado(self._id, "firmando")
            palabra = self._palabras[self._ciclo % len(self._palabras)]
            otras = [p for p in self._palabras if p != palabra][:2]
            self._id += 1
            if self._ciclo % 4 == 3:
                top3 = [_cand(palabra, 0.46), _cand(otras[0], 0.31), _cand(otras[1], 0.12)]
                return Resultado(self._id, "duda", None, 0.46, top3)
            top3 = [_cand(palabra, 0.93), _cand(otras[0], 0.04), _cand(otras[1], 0.02)]
            return Resultado(self._id, "palabra", palabra, 0.93, top3)
        objetivo = ("1234567" if self.modo == "numeros" else "KARDEX")
        if pos < 5 or pos > 5 + 6 * len(objetivo):
            return Resultado(self._id, "reposo")
        if pos == 5 + 6 * len(objetivo):
            self._id += 1
            texto = objetivo if self.modo == "numeros" else "Kárdex"
            return Resultado(self._id, "palabra", texto, 1.0, [_cand(texto, 1.0)])
        return Resultado(self._id, "letra", parcial=objetivo[:(pos - 5) // 6 + 1])
