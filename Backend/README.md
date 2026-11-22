# Backend LSM-Connect (FastAPI)

Servidor local que corre en la misma computadora de la ventanilla. El video solo pasa por memoria y nunca se guarda. La lógica de reconocimiento vive en el paquete `lsm/` (raíz del proyecto); aquí solo están las rutas.

## Arrancar

Desde la **raíz del proyecto**, con el `venv` activo:

```powershell
python -m uvicorn app.main:app --app-dir Backend --port 8000                       # motor SIMULADO
$env:LSM_MOTOR="real"; python -m uvicorn app.main:app --app-dir Backend --port 8000   # modelos de modelos/
```

Para comprobar que responde: http://localhost:8000/salud. La documentación interactiva está en http://localhost:8000/docs.

## Contrato

### `WS /ws/camara`

**Interfaz → servidor**

- **Binario:** una imagen JPEG por mensaje, sin espejo, de ~640×480 y calidad 0.7. **Se manda la siguiente cuando llega la respuesta de la anterior.**
- **Texto `config`:** `{"tipo": "config", "modo": "senas" | "deletreo" | "numeros", "dominios": ["escolar"]}`. Se manda al conectar y cada vez que cambia el modo; **no hace falta reconectar**. Las señas de `general` siempre están activas.
- **Texto `reiniciar`:** `{"tipo": "reiniciar"}` limpia el estado (al empezar una atención nueva).

**Servidor → interfaz:** un JSON por imagen:

```json
{ "id": 3, "estado": "palabra", "palabra": "Kárdex", "confianza": 0.93,
  "top3": [{"palabra": "Kárdex", "prob": 0.93}, {"palabra": "Constancia", "prob": 0.04}, {"palabra": "Foto", "prob": 0.02}],
  "parcial": "", "aviso": null }
```

| `estado` | Significado | Qué hace la interfaz |
|---|---|---|
| `reposo` | Nadie está firmando | Nada |
| `firmando` | Hay una seña en curso | Indicador "reconociendo…" |
| `letra` | Deletreo en curso; `parcial` trae las letras leídas ("KAR") | Mostrar `parcial` |
| `palabra` | Palabra reconocida; `palabra` ya viene lista para mostrar | Agregarla (una vez por `id`) |
| `duda` | No está seguro | Mostrar `top3` como botones (una vez por `id`) |

- `id` sube en 1 con cada `palabra` o `duda`. **Cada `id` se procesa una sola vez.**
- `aviso` trae un mensaje para la persona cuando algo impide reconocer (por ejemplo, no hay modelo de letras y se eligió deletreo).
- En deletreo, si lo deletreado coincide con el vocabulario se devuelve la palabra bien escrita ("KARDEX" → "Kárdex"). Si se parece, llega `duda` con las opciones más lo deletreado tal cual. Si no se parece a nada (un nombre), se respeta lo deletreado.

### HTTP

| Ruta | Qué hace |
|---|---|
| `GET /salud` | Estado, motor en uso y qué modelos existen |
| `GET /vocabulario?dominios=escolar` | Señas activas (`general` + dominios, con `texto` y `tramite`) y respuestas rápidas |

## Estructura

- `app/main.py`: rutas y WebSocket. Los modelos se cargan una sola vez y se comparten entre conexiones.
- `app/contrato.py`: formato de los mensajes.
- Motor real y simulado: `lsm/motor.py`.
