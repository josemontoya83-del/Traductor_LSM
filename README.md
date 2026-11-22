# LSM-Connect

Sistema que reconoce **Lengua de Señas Mexicana (LSM)** con una cámara y la muestra como texto en español, para ventanillas de atención. El alumno se comunica con **señas** o **deletreando**; el empleado lee el texto y responde con frases rápidas (en texto y, si existe, en **video en LSM**).

Proyecto del Grupo 952, UABC Ensenada. Primer lugar de uso: **Servicios Escolares**.

> **Estado:** listo para **grabar el dataset con personas sordas** (ver [`protocolo/PROTOCOLO_GRABACION.md`](protocolo/PROTOCOLO_GRABACION.md)). Todavía no hay modelos entrenados: se generan con esas grabaciones. Mientras tanto, la interfaz funciona en modo simulado.

---

## Cómo se extiende más allá de Servicios Escolares

El motor no está atado a Servicios Escolares. El vocabulario está en capas:

```
┌──────────────────────────────────────────────────────────────┐
│ DELETREO (alfabeto + números)               funciona en TODO │
│   Cualquier palabra, nombre, carrera o matrícula, sin grabar │
│   nada nuevo. Si lo deletreado se parece a una palabra       │
│   conocida, se corrige ("KARDES" -> "Kárdex").               │
├──────────────────────────────────────────────────────────────┤
│ SEÑAS GENERALES (30)                   activas en TODO lugar │
│   hola, gracias, sí, no, ayuda, no entiendo, ¿dónde?, pagar… │
├──────────────────────────────────────────────────────────────┤
│ PAQUETE DEL LUGAR (≈25 señas)            uno por ventanilla  │
│   escolar: kárdex, inscripción, beca, constancia…            │
│   (mañana) biblioteca, caja, clínica…                        │
└──────────────────────────────────────────────────────────────┘
```

- **Señas** para lo frecuente: es lo natural y rápido para una persona sorda.
- **Deletreo** para todo lo demás: es lo que permite usar el sistema en cualquier lugar desde el primer día.
- **Llevarlo a otro lugar** = crear `vocabulario/dominios/<lugar>.json` con ~20–30 señas, grabarlas con el mismo protocolo y reentrenar. El deletreo y las señas generales ya funcionan ahí. Cada ventanilla elige su paquete en la URL: `http://localhost:5173/?dominio=biblioteca`.

## Cómo funciona

```
Cámara ─JPEG─► Servidor local (FastAPI) ── lsm/ (paquete compartido) ─────────────────────┐
                 │  MediaPipe Holistic: manos, cuerpo y cara (lsm/puntos.py)              │
                 │  Segmentador: ¿empezó / terminó la seña? (lsm/segmentador.py)          │
                 ├─ modo SEÑAS:    seña completa ─► modelo de señas ─► palabra            │
                 └─ modo DELETREO: ventana de 0.6 s ─► modelo de letras ─► "K A R D E X"  │
                                   ─► vocabulario ─► "Kárdex"  (lsm/decodificador.py)     │
Pantalla alumno + empleado ◄─────────────────────────────────────────────────────────────┘
```

- La **captura, el entrenamiento y el servidor usan el mismo código** (`lsm/`) para extraer puntos, cortar las señas y calcular rasgos. Lo que el modelo ve al entrenar es exactamente lo que ve en vivo.
- **Zurdos:** todo se pasa a "mano dominante = derecha" con un espejo, así una persona zurda se reconoce igual.
- Si el sistema **no está seguro**, no adivina: muestra 3 opciones para que el alumno toque la correcta.
- **Privacidad en la ventanilla:** el video solo pasa por memoria y nunca se guarda; todo corre en la misma computadora.

## Estructura

```
lsm/                    Paquete compartido: puntos, rasgos, segmentador, modelos, motor en vivo
herramientas/           captura.py, extraer_puntos.py, revisar_datos.py, entrenar_letras.py,
                        entrenar_senas.py, exportar_respuestas.py, detectar_camaras.py
vocabulario/            letras.json, respuestas.json, dominios/general.json, dominios/escolar.json
protocolo/              protocolo.json (qué se graba), PROTOCOLO_GRABACION.md, consentimiento, particion.json
Backend/app/            Servidor FastAPI (main.py) y contrato de mensajes (contrato.py)
Frontend/lsm-connect/   Interfaz React
tests/                  Pruebas automáticas (con datos sintéticos, sin cámara)
modelos/                Modelos entrenados (no se suben a git)
datos/                  Videos y puntos grabados (NO se suben a git)
entregas/               Documentación y prototipos de las entregas del curso
grabar.bat              Menú de grabación para el operador
iniciar_demo.bat        Arranca servidor + interfaz      detener_demo.bat   Apaga todo
```

## Instalación (una sola vez, Windows 10/11)

Requisitos: [Python 3.12 de 64 bits](https://www.python.org/downloads/) y [Node.js](https://nodejs.org/) 18 o superior.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m pytest                # deben pasar todas las pruebas
```

## Uso

| Qué | Cómo |
|---|---|
| **Grabar** (operador) | Doble clic en `grabar.bat` → 1 probar cámara · 2 grabar sesión · 3 ver avance |
| Extraer puntos de lo grabado | `python herramientas\extraer_puntos.py` |
| Ver avance y tomas a repetir | `python herramientas\revisar_datos.py --avisos` |
| Entrenar | `python herramientas\entrenar_letras.py` y `python herramientas\entrenar_senas.py` |
| Prueba final (personas nunca vistas) | los mismos con `--prueba` (ver `protocolo/particion.json`) |
| Videos de respuestas para la interfaz | `python herramientas\exportar_respuestas.py --persona P03` |
| **Demo** | Doble clic en `iniciar_demo.bat` (usa los modelos de `modelos/`; si no hay, simulado) |
| Demo simulada | `iniciar_demo.bat simulado` |
| Otra ventanilla | `iniciar_demo.bat real biblioteca` o `?dominio=biblioteca` en la URL |

Arranque manual, sin `.bat`:

```powershell
$env:LSM_MOTOR="real"; python -m uvicorn app.main:app --app-dir Backend --port 8000
cd Frontend\lsm-connect; npm install; npm run dev
```

Contrato entre interfaz y servidor: [`Backend/README.md`](Backend/README.md).

## Cómo se evalúa

- **Siempre dejando personas fuera:** la persona de prueba nunca se vio al entrenar (validación cruzada por persona).
- La validación para detener el entrenamiento se separa **antes** del aumento de datos y por persona.
- 2 personas quedan apartadas para la **prueba final** (`protocolo/particion.json`); con ellas nunca se entrena.
- El deletreo se mide reproduciendo palabras reales (bloque E) por el mismo motor del servidor: error por letra y palabras correctas.

## Limitaciones conocidas

- Reconoce **palabras sueltas** (señas o deletreadas), no frases completas con gramática de LSM.
- La expresión facial se guarda en los datos (subconjunto de la malla facial), pero los modelos aún no la usan.
- La interfaz manda una imagen a la vez y espera la respuesta: con MediaPipe en CPU se logran ~10–15 imágenes por segundo. Para deletrear rápido conviene una computadora con buen procesador.
