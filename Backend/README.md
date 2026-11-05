# Backend LSM-Connect (FastAPI)

Servidor local que corre en la misma máquina de la ventanilla (Edge). El video solo pasa por RAM y no se guarda.

## Arrancar

Desde esta carpeta (`Backend/`), con el entorno `venv` activo:

```powershell
pip install -r requirements-backend.txt          # una sola vez
uvicorn app.main:app --port 8000                  # motor SIMULADO (para desarrollar el front)
$env:LSM_MOTOR="real"; uvicorn app.main:app --port 8000   # motor REAL (requiere Modelo_ia/lsm_tramites.h5)
```

Comprobar: abrir http://localhost:8000/salud → `{"ok":true,"motor":"simulado"}`. Documentación interactiva: http://localhost:8000/docs

El motor simulado devuelve palabras falsas en un ciclo fijo; el front se desarrolla contra él y después se cambia a `real` sin tocar nada.

## Contrato

### `WS /ws/camara` (señas → texto)

- **Front → backend:** cada mensaje binario es **un frame JPEG** (sin espejo, tal como lo da la cámara; ~640×480, calidad 0.7).
- **Backend → front:** por cada frame, un JSON:

```json
{ "id": 3, "estado": "palabra", "palabra": "kardex", "confianza": 0.93,
  "top3": [ {"palabra":"kardex","prob":0.93}, {"palabra":"constancia","prob":0.04}, {"palabra":"foto","prob":0.02} ] }
```

| `estado` | Significado | Qué hace el front |
|---|---|---|
| `reposo` | Nadie está firmando | No mostrar nada nuevo |
| `firmando` | Detectó una seña en curso | Indicador "reconociendo…" |
| `palabra` | Seña reconocida con confianza | Agregar `palabra` al texto/chat (una vez por `id`) |
| `duda` | No está seguro | Mostrar `top3` como botones para que la persona toque la correcta (una vez por `id`) |

- `id` sube en 1 con cada `palabra` o `duda`. En los demás estados repite el último. **Procesar cada evento una sola vez por `id`.**
- **Mandar el siguiente frame cuando llegue la respuesta del anterior** (evita saturar al backend). Con eso se logran unos 10–15 fps, suficiente.
- Texto `{"tipo":"reiniciar"}` limpia el estado interno (usar al iniciar una atención nueva).

```js
const ws = new WebSocket("ws://localhost:8000/ws/camara");
ws.onopen = enviarSiguiente;
ws.onmessage = (e) => { const r = JSON.parse(e.data); manejar(r); enviarSiguiente(); };
async function enviarSiguiente() {
  canvas.getContext("2d").drawImage(video, 0, 0, 640, 480);
  canvas.toBlob((b) => b.arrayBuffer().then((buf) => ws.send(buf)), "image/jpeg", 0.7);
}
```

### `WS /ws/chat?rol=estudiante|ventanilla&sala=principal`

- **Front → backend:** `{"texto": "Hola"}` (máx. 500 caracteres).
- **Backend → front:** al conectar llega `{"tipo":"historial","mensajes":[...]}`; después cada mensaje de la sala:

```json
{ "tipo": "mensaje", "rol": "estudiante", "texto": "Hola", "hora": "2026-11-04T19:40:00+00:00" }
```

- Un mensaje se difunde a **todos** los conectados a esa `sala` (incluido el que lo envió).
- La conversación vive solo en RAM. Al cambiar de modo cámara ↔ chat no se pierde (al reconectar llega el historial).
- Las palabras reconocidas por la cámara (`palabra`, o la elegida en `duda`) se envían como mensajes de chat con `rol: "estudiante"`, así el empleado las ve igual que si fueran escritas.

### Otros

| Ruta | Qué hace |
|---|---|
| `GET /salud` | Estado del servidor y motor en uso |
| `GET /clases` | Lista de palabras que reconoce |
| `POST /chat/{sala}/cerrar` | Fin de la atención: borra la conversación de la RAM y manda `{"tipo":"cerrada"}` a los clientes |

## Estructura

- `app/contrato.py` — formato de los mensajes.
- `app/motores.py` — `MotorSimulado` y `MotorReal` (MediaPipe + modelo + segmentación).
- `app/main.py` — rutas y WebSockets.
