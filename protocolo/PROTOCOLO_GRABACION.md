# Protocolo de grabación con personas sordas

Guía para el equipo: qué graba cada persona, cómo se prepara el lugar y qué se hace antes, durante y después de cada sesión. El programa de captura (`grabar.bat` o `herramientas/captura.py`) sigue este protocolo solo: va mostrando en pantalla qué toca. La fuente de verdad es `protocolo/protocolo.json`; si se cambia algo ahí, hay que actualizar este documento.

---

## 1. Qué graba cada persona

Cada persona graba **2 sesiones**, idealmente en días distintos y con otra ropa (así el modelo no aprende la ropa ni la luz de un día).

| Bloque | Qué se graba | Elementos | Repeticiones sesión 1 | Repeticiones sesión 2 | Tomas sesión 1 | Tomas sesión 2 | Cómo se hace cada toma |
|---|---|---|---|---|---|---|---|
| **A** | Alfabeto manual | 30 letras (A–Z, CH, LL, Ñ, RR) | 2 | 2 | 60 | 60 | Sostener la letra ~2 s y bajar la mano. Las letras con movimiento (CH, J, K, LL, Ñ, Q, RR, X, Z) se hacen **3 veces seguidas**. |
| **B** | Números | 0 a 9 | 2 | 1 | 20 | 10 | Sostener el número ~2 s y bajar la mano. |
| **C** | Señas generales | 30 señas | 3 | 3 | 90 | 90 | Manos abajo → seña → manos abajo. |
| **D** | Señas de Servicios Escolares | 25 señas | 3 | 3 | 75 | 75 | Igual que C. |
| **E** | Palabras deletreadas | 12 palabras distintas en cada sesión | 1 | 1 | 12 | 12 | Deletrear la palabra completa **a su ritmo normal** y bajar la mano. Sirven para *probar* el deletreo. |
| **F** | Movimientos que NO son seña | 6 movimientos | 1 | 1 | 6 | 6 | Rascarse, acomodarse el cabello, ver el celular... (6 s fijos). Enseñan al sistema a no escribir nada. |
| **G** | Respuestas del empleado *(opcional)* | 12 frases | — | 1 | — | 12 | **Solo 1 o 2 personas**, las que mejor firmen según el intérprete. Se muestran como video al alumno. |
| | **Total** | | | | **263** | **253 (+12)** | |

**Por persona en total:** 4 repeticiones de cada letra, 3 de cada número, **6 de cada seña**, 24 palabras deletreadas y 12 movimientos negativos.
**Con 10 personas:** unas 5,200 tomas y 60 ejemplos de cada seña de 10 personas distintas.

### Tiempo estimado

| | Sesión 1 | Sesión 2 |
|---|---|---|
| Grabación pura (~7 s por toma) | ~35 min | ~33 min (+5 min si se hace G) |
| Con explicación, descansos y repeticiones | **~60 min** | **~55 min** |

Hagan un descanso de 5 minutos entre bloques. Si la persona se cansa, se puede salir (Q) y continuar otro día con el mismo comando: el programa sigue donde se quedó.

### Listas completas

**Letras:** A B C CH D E F G H I J K L LL M N Ñ O P Q R RR S T U V W X Y Z
**Números:** 0 1 2 3 4 5 6 7 8 9

**Señas generales (C):** Hola, Gracias, Por favor, Sí, No, Ayuda, No entiendo, Repetir, Esperar, ¿Dónde?, ¿Cuándo?, ¿Cuánto?, ¿Qué?, ¿Cómo?, Quiero, Necesito, Tengo, Pagar, Dinero, Documento, Hoy, Mañana, Nombre, Correo, Teléfono, Problema, Cita, Listo / Terminé, Bien, Perdón

**Señas de Servicios Escolares (D):** Inscripción, Reinscripción, Kárdex, Constancia, Credencial, Foto, Beca, Baja, Certificado, Título, Servicio social, Horario, Materia, Calificación, Semestre, Carrera, Facultad, Maestro, Alumno, Examen, Solicitar, Recoger, Entregar, Firma, Matrícula

**Palabras deletreadas (E):**
- Sesión 1: KARDEX, BECA, UABC, ENSENADA, QUIMICA, ZAPATO, NIÑO, LLAVE, PERRO, TAXI, 1185520, 2026
- Sesión 2: MARIA, GONZALEZ, HECTOR, WIFI, CHOCOLATE, JUGO, YOGUR, FLOR, VIDEO, EXAMEN, 6461234567, 38

Entre las dos sesiones aparecen todas las letras del alfabeto.

**Movimientos negativos (F):** manos quietas; rascarse la cara o la cabeza; acomodarse el cabello o los lentes; sacar el celular y verlo; cruzar y descruzar los brazos; mover las manos sin decir nada.

**Respuestas (G):** Hola, ¿en qué le puedo ayudar? · Pase a caja · Le falta un documento · Regrese mañana · Espere su turno, por favor · Llene este formato · Su trámite está listo · Tarda 3 días hábiles · Necesita su credencial · Necesitamos tomarle una foto · Le avisaremos por correo · ¿Algo más en que le pueda ayudar?

El orden dentro de cada bloque se baraja distinto para cada persona, para que el cansancio no caiga siempre en las mismas señas.

---

## 2. Antes de la primera sesión (una sola vez)

1. **Revisar el vocabulario con el intérprete y 1 o 2 personas sordas.** Para cada seña de las listas C y D:
   - ¿Existe una seña común en la comunidad de Ensenada? Si no hay una clara, quitarla.
   - ¿Falta alguna palabra importante para la ventanilla? Agregarla.
   - Confirmar qué letras llevan movimiento y si usan CH, LL y RR como letras.

   Los cambios se hacen en `vocabulario/dominios/general.json`, `vocabulario/dominios/escolar.json` y `vocabulario/letras.json`. **Después de grabar a la primera persona el vocabulario queda congelado**: si se agrega algo más adelante, tienen que grabarlo todas las personas.
2. **Consentimiento informado.** Adaptar `protocolo/consentimiento_plantilla.md` con su profesor (y el comité de ética, si la universidad lo pide) e imprimir una copia por persona. Debe estar disponible en LSM (el intérprete lo explica).
3. **Lista de códigos en papel.** P01, P02... ↔ nombre de la persona. Esta lista **no se guarda en la computadora ni en el repositorio**; se guarda con los consentimientos.
4. **Probar el equipo:** `grabar.bat` → opción 1 (probar cámara). Debe decir "Encuadre correcto" y más de 20 fps.
5. **Espacio en disco:** cuenten ~1 GB por persona. Midan cuánto ocupa la primera sesión (`datos/videos/P01`) y ajusten.

## 3. Preparar el lugar

| Qué | Cómo |
|---|---|
| Cámara | Webcam externa de 720p o 1080p, sobre la pantalla de la laptop, a la altura del pecho o de los ojos. |
| Distancia | 1.5 a 2 m. Que se vea de la cabeza a la cintura, con espacio arriba y a los lados para las manos (el programa avisa si está muy cerca o muy lejos). |
| Fondo | Liso y sin otras personas atrás. |
| Luz | De frente o desde arriba, **nunca una ventana detrás** de la persona. Sin sombras fuertes en las manos. |
| Ropa | Lisa y que contraste con la piel (sin estampados). En la sesión 2, ropa distinta. |
| Postura | Sesión 1 sentado, sesión 2 de pie (o al revés). |
| Pantalla | Mirando a la persona que firma: ahí ve qué seña toca. |
| Roles | **Operador**: maneja el teclado, al lado, fuera de cuadro. **Intérprete**: explica cada bloque y valida que la seña sea correcta. |

## 4. Durante la sesión

1. Abrir `grabar.bat` → opción 2 → código de la persona (P01...) → sesión (1 o 2).
2. La primera vez, el programa pide los datos de la persona (mano dominante, rango de edad, etc.). **No se escribe el nombre.**
3. Por cada toma:
   - La pantalla muestra qué hacer (p. ej. **"Haz la seña: KÁRDEX"**).
   - La persona pone las **manos abajo**. El operador presiona **ESPACIO**.
   - Aparece "Manos abajo... 1.5" y luego **"¡YA!"**: la persona hace la seña y **baja las manos**.
   - La toma termina sola al bajar las manos (o por tiempo).
   - Si sale un aviso en rojo (**REVISAR: ...**), el operador presiona **R** para repetirla.
4. Teclas del operador:

| Tecla | Qué hace |
|---|---|
| ESPACIO | Empezar la toma / terminarla antes |
| R | Repetir la última toma (la borra y la vuelve a pedir) |
| X | Cancelar la toma en curso |
| S | Saltar esta toma (se pide al final) |
| C | Modo continuo: tras una toma correcta empieza sola la siguiente (más rápido cuando ya agarraron ritmo) |
| P | Pausa / descanso |
| Q o ESC | Salir (lo grabado queda guardado) |

5. **Reglas para la persona que firma** (que el intérprete las explique al inicio):
   - Firmar **como lo haría normalmente** en una ventanilla: ni más lento ni exagerado.
   - Si en su comunidad la seña se hace distinto a como la hizo otra persona, **está bien**: lo importante es que sea natural. El intérprete anota en papel la variante (persona, seña y repetición).
   - Empezar y terminar cada toma con las manos abajo.
   - Si se equivoca, avisa y se repite con R.

## 5. Después de cada sesión

```powershell
venv\Scripts\activate
python herramientas\extraer_puntos.py          # saca los puntos de los videos nuevos (~1-2 min por cada 100 tomas)
python herramientas\revisar_datos.py --avisos  # avance por persona y tomas que conviene repetir
```

- Las tomas con avisos se pueden volver a grabar: se borran su `.mp4` y su `.json` de `datos/videos/Pxx/sN/` y se abre la captura con la misma persona y sesión.
- **Respaldar `datos/`** el mismo día en el almacenamiento institucional acordado (Drive de UABC con acceso restringido, disco externo cifrado...). **Nunca subirlo a GitHub** (ya está en `.gitignore`).

## 6. Al terminar con todas las personas

1. Elegir **2 personas para la prueba final** (si hay una persona zurda, que sea una de ellas) y escribirlas en `protocolo/particion.json`:
   ```json
   { "prueba": ["P04", "P09"] }
   ```
   Con ellas **nunca** se entrena: son el número honesto de qué tan bien funciona con alguien nuevo.
2. Entrenar y evaluar:
   ```powershell
   python herramientas\entrenar_letras.py
   python herramientas\entrenar_senas.py
   python herramientas\entrenar_letras.py --prueba
   python herramientas\entrenar_senas.py --prueba
   ```
3. Exportar las respuestas en video (bloque G) de la persona elegida:
   ```powershell
   python herramientas\exportar_respuestas.py --persona P03
   ```

## 7. Ética y privacidad (resumen)

- Solo se graba con el **consentimiento firmado**. La persona puede retirarse cuando quiera: se borra su carpeta `datos/videos/Pxx`, `datos/puntos/Pxx` y su línea en `datos/participantes.json`, y se reentrena.
- Las personas se identifican **solo con un código**. Los nombres viven en papel, con los consentimientos.
- Los videos de respuestas (G) se muestran a otras personas en la ventanilla: requieren un permiso **aparte y explícito** en el consentimiento.
- Se recomienda dar un reconocimiento o pago a cada participante y al intérprete por su tiempo.
