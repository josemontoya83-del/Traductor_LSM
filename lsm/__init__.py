"""
Paquete compartido de LSM-Connect.

Todo lo que convierte cámara -> puntos -> rasgos -> predicción vive aquí y lo usan IGUAL
la captura (herramientas/captura.py), el entrenamiento (herramientas/entrenar_*.py) y el
servidor (Backend/). Si algo de esto cambia, hay que volver a extraer puntos y reentrenar.
"""
