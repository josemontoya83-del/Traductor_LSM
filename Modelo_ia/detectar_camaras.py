"""
detectar_camaras.py
Prueba los primeros índices de cámara y muestra cuál abre cuál,
para saber qué número usar en captura_dataset_tramites.py.
"""
import cv2

for indice in range(4):
    cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)
    if cap.isOpened():
        print(f"Índice {indice}: cámara detectada")
        ok, frame = cap.read()
        if ok:
            cv2.imshow(f"Camara indice {indice}", frame)
            cv2.waitKey(20000)  # muestra 20 segundos
            cv2.destroyAllWindows()
    else:
        print(f"Índice {indice}: no disponible")
    cap.release() 