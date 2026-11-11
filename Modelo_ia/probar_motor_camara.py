"""
probar_motor_camara.py
Prueba el MISMO motor del backend (MotorReal: segmentación + modelo + umbral) directo con la
cámara, SIN navegador ni WebSocket. Sirve para saber dónde está la falla:
  - si aquí reconoce bien y en la página no -> el problema está en el front / navegador.
  - si aquí también falla -> el problema está en la cámara, el encuadre o el modelo.

Uso (raíz del repo, venv activo):
    python Modelo_ia/probar_motor_camara.py            # cámara 0
    python Modelo_ia/probar_motor_camara.py --camara 1
Q = salir.
"""
import argparse
import os
import sys
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "Backend"))
os.environ.setdefault("LSM_DEBUG", "1")  # imprime cada segmento en la consola

from app.motores import MotorReal  # noqa: E402
from captura_dataset_tramites import dibujar  # noqa: E402  (Modelo_ia ya queda en sys.path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--camara", type=int, default=0)
    a = ap.parse_args()

    motor = MotorReal()
    cap = cv2.VideoCapture(a.camara, cv2.CAP_DSHOW)  # igual que al grabar el dataset
    if not cap.isOpened():
        sys.exit(f"No se pudo abrir la cámara {a.camara}")
    ok, frame = cap.read()
    print(f"Cámara {a.camara}: {frame.shape[1]}x{frame.shape[0]}" if ok else "Sin imagen")

    ultimo = "-"
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        resultados = motor._holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        r = motor.procesar_vector(motor._extraer(resultados))
        if r.estado == "palabra":
            ultimo = f"{r.palabra} ({r.confianza:.0%})"
        elif r.estado == "duda":
            ultimo = "DUDA: " + ", ".join(f"{c.palabra} {c.prob:.0%}" for c in r.top3)

        vista = frame.copy()
        dibujar(vista, resultados)
        vista = cv2.flip(vista, 1)  # espejo solo para verse; el motor recibe la imagen SIN espejo
        color = (0, 0, 255) if r.estado == "firmando" else (0, 200, 0)
        cv2.putText(vista, r.estado.upper(), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(vista, ultimo, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.imshow("Motor LSM (Q = salir)", vista)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
