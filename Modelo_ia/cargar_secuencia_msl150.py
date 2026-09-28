"""
cargar_secuencia_msl150.py
Carga una secuencia completa (30 frames x 226 keypoints) del demo subset
de MSL-150, uniendo los .npy individuales de cada frame en orden.
"""
import numpy as np
from pathlib import Path

def cargar_secuencia(carpeta_repeticion: str) -> np.ndarray:
    """
    carpeta_repeticion: ruta a una carpeta de repetición, ej.
    'C:/MSL-150-Dataset/data/sample_npy/hoy/1'
    """
    carpeta = Path(carpeta_repeticion)
    frames = []

    for i in range(30):
        archivo = carpeta / f"{i}.npy"
        if not archivo.exists():
            raise FileNotFoundError(f"Falta el frame {i} en {carpeta}")
        frames.append(np.load(archivo))

    secuencia = np.stack(frames)  # shape esperado: (30, 226)
    assert secuencia.shape == (30, 226), f"Shape inesperado: {secuencia.shape}"
    return secuencia


if __name__ == "__main__":
    ruta = "C:/MSL-150-Dataset/data/sample_npy/hoy/1"
    secuencia = cargar_secuencia(ruta)
    print("Shape de la secuencia:", secuencia.shape)
    print("Primeros 5 valores del frame 0:", secuencia[0][:5]) 
