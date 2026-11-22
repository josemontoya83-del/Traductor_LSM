# Protocolo de grabación con personas sordas

Guía para el equipo. **La persona sorda graba sola** en el navegador (`grabar.bat` → opción 1, o `http://localhost:5173/grabar`): la pantalla le explica todo con dibujos y frases cortas, la toma empieza sola cuando tiene las manos abajo y termina sola cuando las baja. El equipo solo registra a la persona, ajusta la cámara y le entrega la computadora.

El programa sigue `protocolo/protocolo.json` y las palabras salen de `vocabulario/`. Si se cambia algo ahí, hay que actualizar este documento.

---

## 1. Qué graba cada persona

Cada persona graba **2 sesiones**, idealmente en días distintos y con otra ropa.

| Bloque | Qué se graba | Elementos | Sesión 1 | Sesión 2 | Cómo se hace cada toma |
|---|---|---|---|---|---|
| **A** | Alfabeto manual | 30 letras | 2 rep. = 60 tomas | 2 rep. = 60 | Sostener la letra ~2 s y bajar la mano. Las letras con movimiento (CH, J, K, LL, Ñ, Q, RR, X, Z) se hacen **3 veces seguidas**. |
| **B** | Números | 0 a 9 | 2 rep. = 20 | 1 rep. = 10 | Sostener el número ~2 s y bajar la mano. |
| **C** | Señas generales | 30 | 3 rep. = 90 | 3 rep. = 90 | Manos abajo → seña → manos abajo. |
| **D** | Señas de Servicios Escolares | 25 | 3 rep. = 75 | 3 rep. = 75 | Igual que C. |
| **E** | Palabras deletreadas | 12 distintas por sesión | 12 | 12 | Deletrear la palabra completa a su ritmo normal. Sirven para *probar* el deletreo. |
| **F** | Movimientos que NO son seña | 6 | 6 | 6 | 6 s fijos. Enseñan al sistema a no escribir nada. |
| **G** | Frases del empleado *(opcional)* | 12 | — | 12 | **Solo 1 o 2 personas**, las que mejor firmen según el intérprete. Se muestran como video al alumno. |
| | **Total** | | **263 (~45 min)** | **253 (~45 min)** | |

**Por persona:** 4 repeticiones de cada letra, 3 de cada número, **6 de cada seña**, 24 palabras deletreadas y 12 movimientos negativos.
**Con 10 personas:** unas 5,200 tomas y 60 ejemplos de cada seña.

Cada toma tarda unos 8 a 10 s: lectura de la palabra (2–4 s), cuenta 3-2-1 y la seña. La pantalla muestra cuánto falta de cada bloque y deja descansar entre bloques.

### Las palabras exactas

**Letras (A):** A B C CH D E F G H I J K L LL M N Ñ O P Q R RR S T U V W X Y Z
**Números (B):** 0 1 2 3 4 5 6 7 8 9

**Señas generales (C), activas en cualquier ventanilla:**

| | | | | |
|---|---|---|---|---|
| Hola | Gracias | Por favor | Sí | No |
| Ayuda | No entiendo | Repetir | Esperar | ¿Dónde? |
| ¿Cuándo? | ¿Cuánto? | ¿Qué? | ¿Cómo? | Quiero |
| Necesito | Tengo | Pagar | Dinero | Documento |
| Hoy | Mañana | Nombre | Correo | Teléfono |
| Problema | Cita | Listo | Bien | Perdón |

**Señas de Servicios Escolares (D):**

| | | | | |
|---|---|---|---|---|
| Inscripción | Reinscripción | Kárdex | Constancia | Credencial |
| Foto | Beca | Baja | Certificado | Título |
| Servicio social | Horario | Materia | Calificación | Semestre |
| Carrera | Facultad | Maestro | Alumno | Examen |
| Solicitar | Recoger | Entregar | Firma | Matrícula |

Las palabras que se pueden confundir llevan una **pista** debajo durante la grabación. Por ejemplo, *Baja* muestra "Dar de baja una materia o la carrera" y *Kárdex*, "Historial de calificaciones". Las pistas se editan en el campo `pista` de los JSON de `vocabulario/dominios/`.

**Palabras deletreadas (E):**
- Sesión 1: KARDEX, BECA, UABC, ENSENADA, QUIMICA, ZAPATO, NIÑO, LLAVE, PERRO, TAXI, 1185520, 2026
- Sesión 2: MARIA, GONZALEZ, HECTOR, WIFI, CHOCOLATE, JUGO, YOGUR, FLOR, VIDEO, EXAMEN, 6461234567, 38

Entre las dos sesiones aparecen todas las letras.

**Movimientos negativos (F):** manos quietas; rascarse la cara o la cabeza; acomodarse el cabello o los lentes; sacar el celular y verlo; cruzar y descruzar los brazos; mover las manos sin decir nada.

**Frases del empleado (G):** Hola, ¿en qué le puedo ayudar? · Pase a caja · Le falta un documento · Regrese mañana · Espere su turno, por favor · Llene este formato · Su trámite está listo · Tarda 3 días hábiles · Necesita su credencial · Necesitamos tomarle una foto · Le avisaremos por correo · ¿Algo más en que le pueda ayudar?

El orden dentro de cada bloque se baraja distinto para cada persona.

---

## 2. Antes de la primera sesión (una sola vez)

1. **Revisar las palabras con el intérprete y 1 o 2 personas sordas.** Para cada seña de C y D:
   - ¿Hay una seña común en la comunidad de Ensenada? Si no hay una clara, quitarla.
   - ¿Falta alguna palabra importante para la ventanilla? Agregarla.
   - ¿La pista se entiende? Confirmar qué letras llevan movimiento y si usan CH, LL y RR.

   Se edita en `vocabulario/dominios/general.json`, `vocabulario/dominios/escolar.json` y `vocabulario/letras.json`. **Después de grabar a la primera persona, las palabras quedan congeladas.**
2. **Videos de instrucciones en LSM (recomendado).** El intérprete graba unos videos cortos que la pantalla muestra solos. Ver `Frontend/lsm-connect/public/instrucciones/LEEME.md`: `bienvenida.mp4` explica los 4 pasos y `bloque_A.mp4` a `bloque_G.mp4` explican cada bloque. Con eso, las instrucciones llegan en su lengua y no solo en texto. Para palabras muy ambiguas se puede poner un video de ejemplo (`public/ejemplos/`), pero solo en esas palabras: si todas tienen ejemplo, todos copian la misma variante.
3. **Consentimiento informado.** Adaptar `protocolo/consentimiento_plantilla.md` con su profesor e imprimir una copia por persona.
4. **Lista de códigos en papel:** P01, P02... ↔ nombre. **Nunca en la computadora.**
5. **Probar el equipo:** `grabar.bat` → opción 1 → hacer la sesión de prueba con alguien del equipo (código P99), revisar con la opción 2 y borrar `datos/videos/P99` y `datos/participantes/P99.json`.
6. **Espacio en disco:** cuenten ~0.5–1 GB por persona. Midan la primera sesión y ajusten.

## 3. Preparar el lugar

| Qué | Cómo |
|---|---|
| Computadora | Laptop con **Chrome o Edge**. Webcam externa de 720p si la de la laptop es mala. |
| Posición | La persona **sentada a una mesa**, con la laptop enfrente a 80–100 cm, para que alcance a tocar los botones. Que se vea de la cabeza a la cintura, con espacio para las manos (la pantalla avisa si está cerca o lejos). |
| Fondo | Liso y sin otras personas atrás. |
| Luz | De frente o desde arriba, **nunca una ventana detrás**. |
| Ropa | Lisa y que contraste con la piel. En la sesión 2, otra ropa. |
| Varias computadoras | Se puede grabar a varias personas a la vez, cada una en su laptop. Al final se juntan las carpetas `datos/` en una sola (cada persona tiene las suyas y no chocan). |

## 4. La sesión, paso a paso

**Lo hace el equipo (2–3 minutos):**
1. `grabar.bat` → **1**. Se abre la pantalla del equipo en el navegador (la primera vez el navegador pide permiso para la cámara: "Permitir").
2. Escribir el **código** (P01) y elegir la **sesión**.
3. La primera vez se registra a la persona: mano dominante, rango de edad, etc., y se marca que **firmó el consentimiento**. No se escribe el nombre.
4. Dejar marcada la **práctica** si es su primera vez.
5. Tocar **Entregar a la persona**.

**Lo hace la persona sorda, sola:**

| Pantalla | Qué ve |
|---|---|
| Así se graba | 4 dibujos: sentarse frente a la cámara · manos abajo · ¡AHORA! = hacer la seña · bajar las manos. Y el video del intérprete, si existe. |
| Revisa la cámara | Su imagen con una figura para acomodarse y un aviso: "¡Perfecto! Te vemos bien" o "Acércate un poco". |
| Práctica | 2 pruebas que **no se guardan** (Hola y la letra A). |
| Inicio de cada bloque | Dibujo, explicación corta y cuántas tomas faltan. Al terminar un bloque: "¡Terminaste! Descansa un momento." |
| Cada toma | La palabra en grande (con su pista) a la izquierda y su cámara a la derecha. Con las manos abajo empieza sola: **3, 2, 1, ¡AHORA!**, el borde rojo y "● GRABANDO". Al bajar las manos aparece **✓ ¡Bien!** y pasa a la siguiente. |
| Si algo salió mal | Un aviso con ícono, por ejemplo "No vimos tu mano levantada", y dos botones: **Repetir** o **Seguir así**. |

Botones siempre a la mano: **Pausa** (tecla ESPACIO), **Repetir la anterior** (tecla R), **No la conozco** (en las señas: la salta; al final puede intentarlas de nuevo) y **Terminé** (mientras graba, para las frases largas). En la pausa está **Terminar por hoy**: lo grabado queda guardado y la próxima vez sigue donde se quedó.

**El equipo puede estar cerca pero no encima.** Conviene que el intérprete esté al inicio (práctica y primer bloque) y luego se quede disponible por si hay dudas.

## 5. Al terminar el día

`grabar.bat` → **3** (sacar los puntos) y luego **2** (ver avance y tomas con avisos). O en PowerShell:

```powershell
venv\Scripts\activate
python herramientas\extraer_puntos.py
python herramientas\revisar_datos.py --avisos
```

**Respaldar `datos/`** el mismo día en el almacenamiento institucional acordado. **Nunca subirlo a GitHub** (ya está en `.gitignore`).

## 6. Al terminar con todas las personas

1. Elegir **2 personas para la prueba final** (si hay una zurda, que sea una de ellas) y escribirlas en `protocolo/particion.json`: `{ "prueba": ["P04", "P09"] }`. Con ellas **nunca** se entrena.
2. Entrenar y evaluar:
   ```powershell
   python herramientas\entrenar_letras.py
   python herramientas\entrenar_senas.py
   python herramientas\entrenar_letras.py --prueba
   python herramientas\entrenar_senas.py --prueba
   ```
3. Exportar las frases en video (bloque G): `python herramientas\exportar_respuestas.py --persona P03`

## 7. Ética y privacidad (resumen)

- Solo se graba con el **consentimiento firmado** (la pantalla del equipo no deja seguir sin marcarlo). La persona puede retirarse cuando quiera: se borran `datos/videos/Pxx`, `datos/puntos/Pxx` y `datos/participantes/Pxx.json`, y se reentrena.
- Las personas se identifican **solo con un código**; los nombres viven en papel.
- Los videos del bloque G se muestran a otras personas: requieren un permiso **aparte y explícito**.
- Se recomienda dar un reconocimiento o pago a cada participante y al intérprete.

---

### Alternativa: programa clásico con operador

Si el navegador da problemas, `grabar.bat` → **4** abre el programa de escritorio. Ahí un operador maneja el teclado (ESPACIO graba, R repite, S salta, C modo continuo, P pausa, Q sale) y la persona solo firma. Guarda los datos en el mismo formato.
