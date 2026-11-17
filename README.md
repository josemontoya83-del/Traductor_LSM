# LSM-Connect: Traductor de LSM a español

Sistema que reconoce señas de la **Lengua de Señas Mexicana (LSM)** con una cámara y las muestra como **texto en español** en tiempo real. Está pensado para la ventanilla de Servicios Escolares: un estudiante sordo hace señas y el empleado las lee en su pantalla, y puede responder con texto o frases rápidas.

Proyecto del Grupo 952, UABC Ensenada.

> **Estado:** prueba de concepto. Reconoce **14 palabras sueltas** de trámites escolares. Funciona bien con las personas que grabaron el dataset; con personas nuevas la precisión baja mucho (ver [Resultados](#resultados)).

---

## Cómo funciona

```
Cámara (navegador) ──JPEG por WebSocket──► Servidor local (FastAPI)
                                              │
                                              ├─ MediaPipe Holistic: 226 puntos por imagen
                                              │  (21 de cada mano x 3 + 25 del cuerpo x 4)
                                              ├─ Segmentación: detecta dónde empieza y termina la seña
                                              ├─ Ajuste a 30 cuadros + normalización por hombros
                                              └─ Red GRU (TensorFlow) ──► palabra + 3 mejores opciones
                                                          │
Pantalla del alumno y del empleado ◄──────────────────────┘
```

- Si el modelo tiene **menos de 70 % de confianza**, no adivina: muestra las 3 opciones más probables para que el alumno elija.
- **Privacidad:** el video solo pasa por la memoria y **nunca se guarda**. Todo corre en la misma computadora; nada sale a internet.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Interfaz | React 18 + Vite 5 |
| Comunicación | WebSockets |
| Servidor | Python 3.12 + FastAPI + Uvicorn |
| Visión | MediaPipe Holistic 0.10 + OpenCV |
| Modelo | TensorFlow 2.17 / tf_keras: red recurrente GRU (~61 mil parámetros) |

## Requisitos

- Windows 10 u 11 con cámara web.
- [Python 3.12](https://www.python.org/downloads/).
- [Node.js](https://nodejs.org/) 18 o superior.

## Instalación (una sola vez)

Desde la carpeta del proyecto, en PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -r Backend\requirements-backend.txt
```

Las librerías de la interfaz (`npm install`) se instalan solas la primera vez que se ejecuta `iniciar_demo.bat`.

## Uso

| Acción | Cómo |
|---|---|
| Iniciar el demo (modelo real) | Doble clic en `iniciar_demo.bat` |
| Iniciar con predicciones simuladas (sin modelo) | `iniciar_demo.bat simulado` |
| Iniciar en modo diagnóstico | `iniciar_demo.bat debug` (ver [Diagnóstico](#diagnóstico)) |
| Apagar todo | Doble clic en `detener_demo.bat` |

`iniciar_demo.bat` abre dos ventanas negras (**LSM Backend** y **LSM Frontend**), espera a que el servidor cargue el modelo (unos 25 s) y abre `http://localhost:5173` en el navegador. No cierres las ventanas negras mientras uses el demo.

<details>
<summary>Arrancar a mano, sin el .bat</summary>

```powershell
# Terminal 1: servidor
cd Backend
$env:LSM_MOTOR="real"; ..\venv\Scripts\python -m uvicorn app.main:app --port 8000

# Terminal 2: interfaz
cd Frontend\lsm-connect
npm install
npm run dev
```

La documentación de los mensajes entre la interfaz y el servidor está en [Backend/README.md](Backend/README.md).
</details>

### Cómo hacer las señas

1. Colócate de modo que se vean tu **cabeza, hombros y pecho**.
2. Haz las señas con la **mano derecha**.
3. Al terminar cada seña, **baja las manos** y espera un segundo. Así el sistema sabe que la seña terminó.

### Palabras que reconoce

Inscripción, Reinscripción, Kárdex, Constancia, Foto, Credencial, Documentos, Solicitar, Recoger, Entrega, Sí, No, Tengo una duda y Gracias.

La lista sale del modelo entrenado (`Modelo_ia/clases_tramites.json`): si se reentrena con otras palabras, la interfaz se actualiza sola.

## Resultados

Dataset propio: **383 grabaciones de 2 personas**, 14 palabras más una clase de "reposo" (12 a 16 repeticiones por palabra y persona).

| Prueba | Resultado |
|---|---|
| Mismas personas, repeticiones no usadas al entrenar (171 muestras) | **81.3 %** a la primera; **88.9 %** con la correcta entre las 3 opciones |
| Frases de 3 a 5 señas (mismas personas) | 18.7 % de error por palabra (distancia de Levenshtein) |
| Persona que el modelo no vio (entrenando con la otra) | **6.7 %** y **21.7 %** |

La última fila es el peor caso, porque cada prueba entrena con una sola persona, pero muestra el límite principal: **el modelo no generaliza a personas nuevas**. Para eso hace falta grabar a muchas más personas.

Para reproducir las métricas: `python Modelo_ia/demo_examen.py evaluar` (genera `resultados_demo.json` y `matriz_confusion.png`).

## Grabar señas y entrenar

Todo se ejecuta desde la carpeta del proyecto, con el entorno activo (`venv\Scripts\activate`):

```powershell
# 1. Grabar: pide la seña y tu nombre; usa sola la cámara disponible.
#    ESPACIO = empezar/detener la grabación, Q = salir.
python Modelo_ia\captura_dataset_tramites.py

# 2. Evaluar (mismas personas y persona nueva) y, con --guardar, generar el modelo final
python Modelo_ia\entrenar_modelo.py --guardar
```

Las grabaciones se guardan en `dataset_tramites/<seña>/<persona>_NNN.npy`: solo coordenadas de puntos, sin video.

## Diagnóstico

| Herramienta | Para qué |
|---|---|
| `iniciar_demo.bat debug` | La ventana del Backend muestra cada seña detectada, su duración y lo que respondió el modelo; además guarda sus puntos en `Pruebas/debug_segmentos/` |
| `python Pruebas\analizar_segmentos.py` | Compara esas señas en vivo contra el dataset: mano usada, duración, si la seña se cerró bien y a qué grabación se parece |
| `python Modelo_ia\probar_motor_camara.py` | Prueba el reconocimiento directo con la cámara, sin navegador |
| `python Modelo_ia\demo_examen.py replay --frase "inscripcion kardex gracias"` | Pasa grabaciones reales por el mismo motor del servidor, sin cámara. Sirve de respaldo si la cámara falla |
| `python Modelo_ia\detectar_camaras.py` | Lista las cámaras conectadas y cuál se usará |

## Estructura del proyecto

```
Backend/app/        Servidor: rutas y WebSockets (main.py), motor de reconocimiento (motores.py)
Frontend/lsm-connect/  Interfaz en React (src/App.jsx)
Modelo_ia/          Captura del dataset, preprocesamiento, entrenamiento y modelo (lsm_tramites.h5)
dataset_tramites/   Grabaciones (puntos) por seña y persona
Pruebas/            Herramientas de diagnóstico
Docs/               Documentación de las entregas
iniciar_demo.bat    Arranca servidor + interfaz
detener_demo.bat    Apaga todo
```

## Limitaciones y trabajo futuro

- Solo **2 personas** en el dataset: hay que grabar a más, idealmente de la comunidad sorda, y validar las señas con intérpretes.
- Reconoce **palabras sueltas**, no frases. La LSM tiene su propia gramática y usa expresiones faciales.
- Mejorar la detección de dónde empieza y termina la seña: algunas señas cortas o hechas con la mano baja se cortan mal, y las de más de 6 s se cortan a la mitad.
- Separar la pantalla del alumno y la del empleado. El servidor ya tiene el chat en tiempo real (`/ws/chat`).
