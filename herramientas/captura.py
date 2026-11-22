"""
captura.py — Programa de grabación para las sesiones con personas sordas.

Uso (desde la carpeta del proyecto, con el venv activo):
    python herramientas/captura.py --persona P01 --sesion 1
    python herramientas/captura.py --persona P01 --sesion 2 --bloques G     # solo un bloque
    python herramientas/captura.py --probar-camara                          # revisar encuadre y luz

Qué hace:
  - Muestra en pantalla qué seña/letra/palabra toca (sigue protocolo/protocolo.json).
  - Graba el VIDEO ORIGINAL (.mp4) de cada toma + un .json con sus metadatos y el tiempo exacto
    de cada cuadro. Los puntos de MediaPipe se sacan después con extraer_puntos.py.
  - Revisa cada toma al momento (¿se vieron los hombros?, ¿se levantó la mano?) y avisa si hay
    que repetirla.
  - Si se cierra a la mitad, al volver a abrirlo continúa donde se quedó.

Controles (los usa el OPERADOR, no la persona que firma):
    ESPACIO  empezar la toma (cuenta regresiva y graba) / terminarla antes
    R        repetir la última toma guardada (la borra y la vuelve a pedir)
    X        cancelar la toma en curso
    S        saltar esta toma (se pide al final)
    C        modo continuo: tras una toma correcta empieza sola la siguiente
    P        pausa / descanso
    Q o ESC  salir (lo grabado queda guardado)
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from lsm import puntos as P  # noqa: E402
from lsm.datos import carpeta_sesion, guardar_participantes, participantes  # noqa: E402
from lsm.protocolo import Toma, cargar_protocolo, tomas as lista_tomas  # noqa: E402
from lsm.rasgos import ReferenciaHombros, mano_activa  # noqa: E402

VENTANA = "LSM-Connect - Captura"
ANCHO_PANTALLA = 1280
PAUSA_AUTO_STOP = 0.8   # s con manos abajo, después de firmar, para terminar la toma sola
MIN_ACTIVO_S = 0.3      # s de mano levantada para considerar que ya firmó
PATRON_PERSONA = re.compile(r"^P\d{2,3}$")


# ====================================================================== cámara (hilo aparte)
class Camara:
    """Lee la cámara en un hilo propio y escribe el video SIN perder cuadros, aunque MediaPipe
    (en el hilo principal) vaya más lento."""

    def __init__(self, fuente, ancho=1280, alto=720, fps=30) -> None:
        self.es_archivo = not isinstance(fuente, int)
        if self.es_archivo:
            self.cap = cv2.VideoCapture(str(fuente))
            self._fps_archivo = self.cap.get(cv2.CAP_PROP_FPS) or 30
        else:
            api = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
            self.cap = cv2.VideoCapture(fuente, api)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
            self.cap.set(cv2.CAP_PROP_FPS, fps)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara/fuente {fuente!r}. "
                               "Revisa que esté conectada o usa --camara con otro número.")
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("La cámara se abrió pero no entrega imagen.")
        self.alto, self.ancho = frame.shape[:2]
        self._lock = threading.Lock()
        self._ultimo, self._t_ultimo, self.n = frame, time.monotonic(), 1
        self._writer = None
        self._tiempos: list[float] = []
        self._vivo = True
        self._hilo = threading.Thread(target=self._leer, daemon=True)
        self._hilo.start()
        self.fps = self._medir_fps()

    def _leer(self) -> None:
        t_prev = time.monotonic()
        while self._vivo:
            ok, frame = self.cap.read()
            if not ok:
                if self.es_archivo:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.01)
                continue
            if self.es_archivo:  # simula tiempo real al leer un archivo (pruebas)
                espera = 1 / self._fps_archivo - (time.monotonic() - t_prev)
                if espera > 0:
                    time.sleep(espera)
                t_prev = time.monotonic()
            t = time.monotonic()
            with self._lock:
                self._ultimo, self._t_ultimo = frame, t
                self.n += 1
                if self._writer is not None:
                    self._writer.write(frame)
                    self._tiempos.append(t)

    def _medir_fps(self, segundos: float = 1.5) -> float:
        n0, t0 = self.n, time.monotonic()
        time.sleep(segundos)
        return round((self.n - n0) / (time.monotonic() - t0), 2)

    def leer(self):
        with self._lock:
            return self._ultimo, self._t_ultimo, self.n

    def iniciar_grabacion(self, ruta: Path) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), max(self.fps, 1.0),
                                 (self.ancho, self.alto))
        if not writer.isOpened():
            raise RuntimeError(f"No se pudo crear el video {ruta}")
        with self._lock:
            self._tiempos = []
            self._writer = writer

    def detener_grabacion(self) -> list[float]:
        with self._lock:
            writer, self._writer = self._writer, None
            tiempos, self._tiempos = self._tiempos, []
        if writer is not None:
            writer.release()
        return tiempos

    def cerrar(self) -> None:
        self._vivo = False
        self._hilo.join(timeout=2)
        self.detener_grabacion()
        self.cap.release()


# ====================================================================== dibujo
def _fuente(tam: int, negrita=False):
    nombres = (["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"] if negrita else []) + \
              ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"]
    for n in nombres:
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default(size=tam)


class Lienzo:
    """Texto con acentos y Ñ (cv2.putText no los soporta)."""

    def __init__(self) -> None:
        self._f = {}

    def f(self, tam, negrita=False):
        clave = (tam, negrita)
        if clave not in self._f:
            self._f[clave] = _fuente(tam, negrita)
        return self._f[clave]

    def dibujar(self, img: np.ndarray, textos: list[tuple]) -> np.ndarray:
        """textos: (texto, (x, y), tamaño, color BGR, negrita, ancla) ; ancla PIL p. ej. 'mm', 'la'."""
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(pil)
        for texto, xy, tam, color, negrita, ancla in textos:
            d.text(xy, texto, font=self.f(tam, negrita), fill=color[::-1], anchor=ancla,
                   stroke_width=2 if tam >= 40 else 0, stroke_fill=(0, 0, 0))
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def dibujar_esqueleto(img, res) -> None:
    import mediapipe as mp

    dib, hol = mp.solutions.drawing_utils, mp.solutions.holistic
    dib.draw_landmarks(img, res.pose_landmarks, hol.POSE_CONNECTIONS)
    dib.draw_landmarks(img, res.right_hand_landmarks, hol.HAND_CONNECTIONS)
    dib.draw_landmarks(img, res.left_hand_landmarks, hol.HAND_CONNECTIONS)


def revisar_encuadre(cuadro: dict) -> tuple[bool, str]:
    if not P.hay_hombros(cuadro):
        return False, "No se ven los hombros: colócate de frente a la cámara"
    ancho = float(np.linalg.norm(cuadro["pose"][11, :2] - cuadro["pose"][12, :2]))
    if ancho < 0.16:
        return False, "Estás lejos: acércate un poco"
    if ancho > 0.42:
        return False, "Estás muy cerca: aléjate un poco"
    if cuadro["pose"][0, 1] < 0.03:
        return False, "Se corta la cabeza: baja la cámara o aléjate"
    return True, "Encuadre correcto"


# ====================================================================== sesión
class SesionCaptura:
    """Lógica de la captura (sin ventanas, para poder probarla). La ventana solo llama a
    paso() para obtener la imagen y a tecla() con lo que se presiona."""

    def __init__(self, persona: str, sesion: str, tomas: list[Toma], camara: Camara,
                 info_persona: dict, fuente_desc: str = "") -> None:
        self.persona, self.sesion, self.camara = persona, sesion, camara
        self.info_persona, self.fuente_desc = info_persona, fuente_desc
        self.prot = cargar_protocolo()
        self.carpeta = carpeta_sesion(persona, sesion)
        self.total = len(tomas)
        self.pendientes: deque[Toma] = deque(t for t in tomas if not self._ruta(t, ".json").exists())
        self.hechas = self.total - len(self.pendientes)
        self.ultima: Toma | None = None
        self.mensaje_ultima = ""
        self.aviso_ultima = False
        self.estado = "espera" if self.pendientes else "fin"
        self.continuo = False
        self.salir = False
        self._t_estado = time.monotonic()
        self._holistic = P.crear_holistic()
        self._res = None
        self._cuadro = P.vacio()
        self._n_analizado = -1
        self._lienzo = Lienzo()
        self._reiniciar_stats()

    # ---------------------------------------------------------- utilidades
    def _ruta(self, toma: Toma, ext: str) -> Path:
        return self.carpeta / f"{toma.nombre}{ext}"

    @property
    def actual(self) -> Toma | None:
        return self.pendientes[0] if self.pendientes else None

    def _cambiar(self, estado: str) -> None:
        self.estado, self._t_estado = estado, time.monotonic()

    def _reiniciar_stats(self) -> None:
        self._ref = ReferenciaHombros()
        self._st = dict(analizados=0, mano=0, hombros=0, activos=0, activo_al_inicio=False,
                        t_primera_activa=None, t_ultima_activa=None)

    # ---------------------------------------------------------- teclado
    def tecla(self, k: int) -> None:
        c = chr(k).lower() if 0 <= k < 256 else ""
        if c in ("q",) or k == 27:
            if self.estado in ("cuenta", "grabando"):
                self._cancelar()
            self.salir = True
        elif k == 32:
            if self.estado == "espera" and self.actual:
                self._iniciar_toma()
            elif self.estado == "pausa":
                self._cambiar("espera")
            elif self.estado == "grabando":
                self._terminar_toma("operador")
        elif c == "x" and self.estado in ("cuenta", "grabando"):
            self._cancelar()
        elif c == "r" and self.estado == "espera":
            self._repetir_ultima()
        elif c == "s" and self.estado == "espera" and len(self.pendientes) > 1:
            self.pendientes.rotate(-1)
            self.mensaje_ultima, self.aviso_ultima = "Toma saltada: se pedirá al final", False
        elif c == "c":
            self.continuo = not self.continuo
        elif c == "p" and self.estado == "espera":
            self._cambiar("pausa")

    def _cancelar(self) -> None:
        if self.estado in ("cuenta", "grabando"):
            self.camara.detener_grabacion()
            self._ruta(self.actual, ".mp4").unlink(missing_ok=True)
        self.mensaje_ultima, self.aviso_ultima = "Toma cancelada", True
        self.continuo = False
        self._cambiar("espera")

    def _repetir_ultima(self) -> None:
        if self.ultima is None:
            return
        for ext in (".mp4", ".json"):
            self._ruta(self.ultima, ext).unlink(missing_ok=True)
        self.pendientes.appendleft(self.ultima)
        self.hechas -= 1
        self.mensaje_ultima, self.aviso_ultima = f"Se repetirá: {self.ultima.texto}", False
        self.ultima = None

    # ---------------------------------------------------------- análisis (MediaPipe)
    def _analizar(self, frame, n) -> None:
        if n == self._n_analizado:
            return
        self._n_analizado = n
        rgb, rel = P.preparar(frame)
        self._res = self._holistic.process(rgb)
        self._cuadro = P.extraer(self._res, rel)
        if self.estado not in ("cuenta", "grabando"):
            return
        st, t = self._st, time.monotonic()
        ref = self._ref.empujar(self._cuadro["pose"])
        activa = bool(mano_activa(self._cuadro["mano_der"], ref) or mano_activa(self._cuadro["mano_izq"], ref))
        st["analizados"] += 1
        st["mano"] += P.hay_mano(self._cuadro)
        st["hombros"] += P.hay_hombros(self._cuadro)
        if activa and self.estado == "cuenta":
            st["activo_al_inicio"] = True   # tenía la mano arriba antes del "¡YA!"
        elif activa:
            st["activos"] += 1
            st["t_primera_activa"] = st["t_primera_activa"] or t
            st["t_ultima_activa"] = t

    # ---------------------------------------------------------- toma
    def _iniciar_toma(self) -> None:
        """Graba DESDE la cuenta regresiva: así el video siempre trae reposo antes de la seña."""
        self._reiniciar_stats()
        self.mensaje_ultima, self.aviso_ultima = "", False
        self.camara.iniciar_grabacion(self._ruta(self.actual, ".mp4"))
        self._cambiar("cuenta")

    def _revisar_auto_stop(self) -> None:
        toma, st, ahora = self.actual, self._st, time.monotonic()
        if ahora - self._t_estado >= toma.segundos_max:
            self._terminar_toma("tiempo")
        elif (toma.parar_al_bajar and st["t_primera_activa"] is not None
              and st["t_ultima_activa"] - st["t_primera_activa"] >= MIN_ACTIVO_S
              and ahora - st["t_ultima_activa"] >= PAUSA_AUTO_STOP):
            self._terminar_toma("manos_abajo")

    def _calidad(self, toma: Toma, motivo: str) -> dict:
        st = self._st
        n = max(st["analizados"], 1)
        avisos = []
        if st["hombros"] / n < 0.7:
            avisos.append("Casi no se vieron los hombros (revisa el encuadre)")
        if toma.tipo != "negativo":
            if st["activos"] == 0:
                avisos.append("No se vio la mano levantada: ¿se hizo la seña?")
            elif st["mano"] / n < 0.4:
                avisos.append("La mano se detectó poco (luz, fondo o mano fuera de cuadro)")
            if st["activo_al_inicio"]:
                avisos.append("Empezó con la mano arriba: hay que iniciar con las manos abajo")
            if motivo == "tiempo" and toma.parar_al_bajar and st["t_ultima_activa"] and \
                    time.monotonic() - st["t_ultima_activa"] < 0.3:
                avisos.append("Se cortó por tiempo con la mano arriba")
        return dict(deteccion_mano=round(st["mano"] / n, 3), deteccion_hombros=round(st["hombros"] / n, 3),
                    cuadros_activos=st["activos"], avisos=avisos)

    def _terminar_toma(self, motivo: str) -> None:
        toma = self.actual
        tiempos = self.camara.detener_grabacion()
        if len(tiempos) < 5:
            self._ruta(toma, ".mp4").unlink(missing_ok=True)
            self.mensaje_ultima, self.aviso_ultima = "La toma quedó vacía (¿falla la cámara?). Repite.", True
            self._cambiar("espera")
            return
        calidad = self._calidad(toma, motivo)
        t0 = tiempos[0]
        meta = dict(
            persona=self.persona, sesion=self.sesion, bloque=toma.bloque, tipo=toma.tipo,
            etiqueta=toma.etiqueta, texto=toma.texto, repeticion=toma.repeticion,
            movimiento=toma.movimiento, modo=toma.modo,
            mano_dominante=self.info_persona.get("mano_dominante"),
            fecha=datetime.now().isoformat(timespec="seconds"), fuente=self.fuente_desc,
            ancho=self.camara.ancho, alto=self.camara.alto, fps_contenedor=self.camara.fps,
            n_cuadros=len(tiempos), duracion_s=round(tiempos[-1] - t0, 3), motivo_fin=motivo,
            version_protocolo=self.prot["version"], calidad=calidad,
            tiempos=[round(t - t0, 4) for t in tiempos])
        self._ruta(toma, ".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self.pendientes.popleft()
        self.hechas += 1
        self.ultima = toma
        if calidad["avisos"]:
            self.mensaje_ultima = "REVISAR: " + " | ".join(calidad["avisos"]) + "  (R = repetir)"
            self.aviso_ultima = True
            self.continuo = False
        else:
            self.mensaje_ultima, self.aviso_ultima = f"Guardada: {toma.texto} ({meta['duracion_s']:.1f} s)", False
        self._cambiar("espera" if self.pendientes else "fin")

    # ---------------------------------------------------------- ciclo
    def paso(self) -> np.ndarray:
        frame, _, n = self.camara.leer()
        self._analizar(frame, n)
        ahora = time.monotonic()
        if self.estado == "cuenta" and ahora - self._t_estado >= self.prot["cuenta_regresiva_s"]:
            self._cambiar("grabando")
        elif self.estado == "grabando":
            self._revisar_auto_stop()
        elif (self.estado == "espera" and self.continuo and self.actual and not self.aviso_ultima
              and ahora - self._t_estado >= 1.2):
            self._iniciar_toma()
        return self._dibujar(frame)

    def _dibujar(self, frame) -> np.ndarray:
        img = frame.copy()
        if self._res is not None:
            dibujar_esqueleto(img, self._res)
        img = cv2.flip(img, 1)  # espejo SOLO en pantalla; el video se guarda sin espejo
        escala = ANCHO_PANTALLA / img.shape[1]
        img = cv2.resize(img, (ANCHO_PANTALLA, round(img.shape[0] * escala)))
        h, w = img.shape[:2]
        BLANCO, AMARILLO, ROJO, VERDE, GRIS = (255, 255, 255), (0, 215, 255), (60, 60, 230), (90, 200, 90), (200, 200, 200)
        textos = []
        toma = self.actual

        cv2.rectangle(img, (0, 0), (w, 150), (25, 25, 25), -1)
        cv2.rectangle(img, (0, h - 70), (w, h), (25, 25, 25), -1)
        if self.estado == "fin":
            textos.append(("¡Sesión terminada! Gracias.", (w // 2, 75), 56, VERDE, True, "mm"))
        elif self.estado == "pausa":
            textos.append(("Descanso", (w // 2, 55), 56, AMARILLO, True, "mm"))
            textos.append(("ESPACIO para continuar", (w // 2, 115), 28, GRIS, False, "mm"))
        elif toma:
            textos.append((toma.instruccion, (w // 2, 30), 28, GRIS, False, "mm"))
            textos.append((toma.texto, (w // 2, 95), 72 if len(toma.texto) < 18 else 40, BLANCO, True, "mm"))
            textos.append((f"Bloque {toma.bloque}: {toma.nombre_bloque} · repetición {toma.repeticion}",
                           (20, 140), 18, GRIS, False, "ls"))

        if self.estado == "cuenta":
            restante = self.prot["cuenta_regresiva_s"] - (time.monotonic() - self._t_estado)
            cv2.rectangle(img, (0, 150), (w - 1, h - 71), (0, 0, 255), 8)
            textos.append((f"Manos abajo... {restante:3.1f}", (w // 2, h // 2), 80, AMARILLO, True, "mm"))
        elif self.estado == "grabando":
            cv2.rectangle(img, (0, 150), (w - 1, h - 71), (0, 0, 255), 8)
            seg = time.monotonic() - self._t_estado
            textos.append((f"● GRABANDO {seg:4.1f} s", (w - 20, 180), 30, ROJO, True, "rm"))
            if seg < 0.8:
                textos.append(("¡YA!", (w // 2, h // 2), 110, VERDE, True, "mm"))
            textos.append(("Al terminar, baja las manos" if toma.parar_al_bajar else "",
                           (w // 2, h - 100), 30, BLANCO, True, "mm"))
        elif self.estado == "espera":
            ok, msg = revisar_encuadre(self._cuadro)
            textos.append((msg, (20, 185), 26, VERDE if ok else AMARILLO, True, "lm"))
            textos.append(("ESPACIO = grabar   R = repetir anterior   S = saltar   C = continuo   P = pausa   Q = salir",
                           (w // 2, h - 100), 20, BLANCO, False, "mm"))

        if self.mensaje_ultima:
            textos.append((self.mensaje_ultima, (20, h - 48), 20, ROJO if self.aviso_ultima else VERDE, True, "lm"))
        estado_cont = "  · CONTINUO" if self.continuo else ""
        textos.append((f"{self.persona} · sesión {self.sesion} · {self.hechas}/{self.total} tomas{estado_cont}",
                       (20, h - 18), 20, GRIS, False, "lm"))
        textos.append((f"{self.camara.ancho}x{self.camara.alto} @ {self.camara.fps:.0f} fps",
                       (w - 20, h - 18), 18, GRIS, False, "rm"))
        return self._lienzo.dibujar(img, textos)

    def cerrar(self) -> None:
        if self.estado in ("cuenta", "grabando"):
            self._cancelar()
        self._holistic.close()


# ====================================================================== registro de la persona
def registrar_persona(persona: str) -> dict:
    datos = participantes()
    if persona in datos:
        info = datos[persona]
        print(f"Persona {persona} ya registrada: mano dominante {info['mano_dominante']}.")
        return info
    print(f"\nRegistro de {persona} (NO se guarda el nombre: solo este código).")
    print("Anota en tu lista de consentimientos, en papel, a quién corresponde este código.\n")
    if input("¿Firmó el consentimiento informado? (s/n): ").strip().lower() != "s":
        raise SystemExit("Sin consentimiento firmado no se puede grabar.")

    def preguntar(texto, opciones=None):
        while True:
            r = input(texto).strip().lower()
            if opciones is None or r in opciones:
                return opciones[r] if isinstance(opciones, dict) else r
            print(f"  Opciones: {', '.join(opciones)}")

    info = dict(
        mano_dominante=preguntar("Mano dominante (d = derecha, i = izquierda): ", {"d": "derecha", "i": "izquierda"}),
        rango_edad=preguntar("Rango de edad (1 = <18, 2 = 18-25, 3 = 26-40, 4 = 41-60, 5 = >60): ",
                             {"1": "<18", "2": "18-25", "3": "26-40", "4": "41-60", "5": ">60"}),
        lsm_lengua_materna=preguntar("¿La LSM es su primera lengua? (s/n): ", {"s": True, "n": False}),
        anos_usando_lsm=preguntar("Años usando LSM (número aproximado): "),
        region=preguntar("Ciudad/región donde aprendió LSM (p. ej. Ensenada): "),
        consentimiento=True, fecha_registro=datetime.now().isoformat(timespec="seconds"),
        notas=preguntar("Notas (opcional, Enter para omitir): "))
    datos[persona] = info
    guardar_participantes(datos)
    return info


# ====================================================================== main
def abrir_camara(args) -> tuple[Camara, str]:
    if args.fuente:
        return Camara(args.fuente), str(args.fuente)
    indice = args.camara
    if indice is None:
        from herramientas.detectar_camaras import primera_camara_disponible

        indice = primera_camara_disponible()
        if indice is None:
            raise SystemExit("No se encontró ninguna cámara.")
    cam = Camara(indice, args.ancho, args.alto, 30)
    return cam, f"camara:{indice}"


def probar_camara(args) -> None:
    cam, desc = abrir_camara(args)
    print(f"Cámara {desc}: {cam.ancho}x{cam.alto} a {cam.fps} fps. Q para salir.")
    if cam.fps < 20:
        print("AVISO: menos de 20 fps. Mejora la luz o prueba --ancho 640 --alto 480.")
    holistic, lienzo = P.crear_holistic(), Lienzo()
    try:
        while True:
            frame, _, _ = cam.leer()
            rgb, rel = P.preparar(frame)
            res = holistic.process(rgb)
            cuadro = P.extraer(res, rel)
            img = frame.copy()
            dibujar_esqueleto(img, res)
            img = cv2.flip(img, 1)
            ok, msg = revisar_encuadre(cuadro)
            manos = ("der " if cuadro["mano_der"].any() else "") + ("izq" if cuadro["mano_izq"].any() else "")
            img = lienzo.dibujar(img, [(msg, (15, 30), 26, (90, 200, 90) if ok else (0, 215, 255), True, "lm"),
                                       (f"Manos detectadas: {manos or 'ninguna'} · {cam.fps:.0f} fps",
                                        (15, 65), 20, (255, 255, 255), False, "lm")])
            cv2.imshow(VENTANA, img)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    finally:
        cam.cerrar()
        cv2.destroyAllWindows()


def main() -> None:
    ap = argparse.ArgumentParser(description="Grabación de señas para LSM-Connect")
    ap.add_argument("--persona", help="Código anónimo, p. ej. P01")
    ap.add_argument("--sesion", help="Número de sesión del protocolo (1 o 2)")
    ap.add_argument("--bloques", help="Solo estos bloques, p. ej. A,B o G")
    ap.add_argument("--camara", type=int, help="Índice de la cámara (por defecto, la primera disponible)")
    ap.add_argument("--fuente", help="(pruebas) usar un archivo de video en lugar de la cámara")
    ap.add_argument("--ancho", type=int, default=1280)
    ap.add_argument("--alto", type=int, default=720)
    ap.add_argument("--probar-camara", action="store_true", help="solo revisar encuadre, luz y fps")
    args = ap.parse_args()

    if args.probar_camara:
        return probar_camara(args)
    if not args.persona or not args.sesion:
        ap.error("Indica --persona y --sesion (o usa --probar-camara).")
    persona = args.persona.upper()
    if not PATRON_PERSONA.match(persona):
        ap.error("La persona debe ser un código como P01 (nunca el nombre real).")
    bloques = [b.strip().upper() for b in args.bloques.split(",")] if args.bloques else None

    tomas = lista_tomas(persona, args.sesion, bloques)
    if not tomas:
        raise SystemExit("No hay tomas para esa combinación de sesión/bloques.")
    info = registrar_persona(persona)
    cam, desc = abrir_camara(args)
    print(f"Cámara: {cam.ancho}x{cam.alto} a {cam.fps} fps")
    if cam.fps < 20:
        print("AVISO: la cámara da menos de 20 fps. Mejora la luz o usa --ancho 640 --alto 480.")
    sesion = SesionCaptura(persona, args.sesion, tomas, cam, info, desc)
    print(f"{sesion.hechas}/{sesion.total} tomas ya grabadas. Se abre la ventana de captura.")
    cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)
    try:
        while not sesion.salir:
            cv2.imshow(VENTANA, sesion.paso())
            k = cv2.waitKey(1)
            if k != -1:
                sesion.tecla(k & 0xFF)
            if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        sesion.cerrar()
        cam.cerrar()
        cv2.destroyAllWindows()
    print(f"\nGrabadas {sesion.hechas}/{sesion.total} tomas en {sesion.carpeta}")
    if sesion.pendientes:
        print("Para continuar después, vuelve a correr el mismo comando.")


if __name__ == "__main__":
    main()
