## A.1 Estructura del formulario (para el prototipo / interfaz)

- 1. Clasificación del usuario

- Tipo: Super experto - Mainstream - Inexperto

- 2. Perfil

- Alias

- Contexto de uso

- Frecuencia de uso de LSM o de trámites universitarios

- Nivel de habilidad (escala 1 - 10)

- 3. Tareas observadas

- 4. Workarounds — trucos o adaptaciones manuales que ya usa para resolver el problema sin la app.

- 5. Errores / fricciones que este usuario hace más visibles que un usuario normal.

- 6. Necesidad extrema detectada + hipótesis de cómo se generaliza al usuario promedio.

Perfil : Estudiante de licenciatura,100% fluido en LSM(Alias: Alex)

## A.2 Entrevista - Usuario super experto

| Clasificación | Super experto |
| --- | --- |
| Alias | Alex |
| Contexto de uso | Estudiante de licenciatura,100% fluido |
|   | en LSM, realiza trámites de kardex y |
|   | becas en UABC. |
| Frecuencia | 2 a 4 veces por semestre (Entrega y |
|   | seguimiento de beca, Kardex) |
| Nivel de habilidad | 10 |
| Tareas observadas | Al describir cómo sería usar la |
|   | herramienta, se detuvo específicamente |
|   | en la idea de poder hacer preguntas de |
|   | seguimiento (¿de qué semestre?) sin |
|   | quedarse atorado. |
| Workarounds actuales | Lleva a un compañero de carrera que |
|   | aprendió señas con él,y cuando no hay |
|   | nadie disponible,usa notas predefinidas |
|   | guardadas en el celular sobre lo que |
|   | quiere hacer en el trámite. |


| Errores / fricciones que este usuario | No sabe si un malentendido fue error |
| --- | --- |
| hace más visibles que un usuario | suyo o del empleado,porque no hay |
| normal. | forma de aclarar rapido.No lo agrada |
|   | tener que sentirse dependiente de un |
|   | compañero que lo ayude para los |
|   | trámites. |
| Necesidad extrema detectada | Necesita poder resolver preguntas de |
|   | seguimiento en tiempo real(¿que |
|   | semestre?) sin quedarse atorado, y |
|   | necesita una confirmación real y clara |
|   | de que su trámite quedó completo antes |
|   | de irse de la ventanilla. |
| Hipótesis de generalización | Si incluso un usuario experto en LSM |
|   | valora mucho tener una confirmación |
|   | clara del trámite,una confirmación real y |
|   | clara beneficiaría tanto a alguien |
|   | experto en LSM como a alguien que no |
|   | lo es. |

## A.3 Entrevista - Usuario inexperto

| Clasificación | Inexperto |
| --- | --- |
| Alias | Empleado A |
| Contexto de uso | Empleado de ventanilla en UABC;muy rara |
|   | vez ha atendido a un alumno con |
|   | discapacidad auditiva o del habla. |
| Frecuencia | Rara vez atiende alumnos de LSM . |
| Nivel de habilidad | 1 |
| Tareas observadas | Muestra preocupación específica sobre qué |
|   | pasaría si una palabra no se traduce |
|   | correctamente, pero no rechaza la idea una |
|   | vez que entiende lo simple que sería. |
| Workarounds actuales | Pide al usuario que lo escriba en un bloc de |
|   | notas y que se lo muestre. |
| Errores / fricciones que este usuario | El trámite tarda más porque el modelo de |
| hace más visibles que un usuario | comunicación es escrito , que es mucho |
| normal. | más lento que hablar directamente. |
| Necesidad extrema detectada | Teme no saber usar la herramienta o no |
|   | poder adaptarse a un nuevo modelo de |


| trabajo,también le preocupa que pasa si el |
| --- |
| sistema traduce mal una palabra y el error |
| pasa desapercibido. |
| Hipótesis de generalización Si un empleado con cero experiencia en el |
| ámbito de LSM,logra sentirse agusto con |
| interfaz simple y el feedback claro antes |
| errores de traducción de señas,el personal |
| con un poco más de experiencia se |
| adaptara a esa nueva forma de trabajo |
| mucho más rápido. |

*Parte B — Fase 2: Task Flows*

- 3 flujos críticos

- 1.Traducir una seña a texto en tiempo real (Alumno -> Empleado)

- 2.Seleccionar el trámite mediante seña(menú inicial)

- 3.Pedir ayuda cuando el alumno no sabe que tramite necesita(seña de duda)

*Flujo 1-Traducir una seña a texto en tiempo real (Alumno -> Empleado)*





![alt text](image.png)





Ruta feliz:Cámara detecta manos de inmediato, seña coincide con vocabulario institucional (25–30 señas del MVP), traducción aparece en < 1 segundo y el usuario confirma sin corregir nada.

Side doors: El usuario puede iniciar el flujo deletreando con dactilología si la seña no está en el vocabulario institucional; el empleado también puede iniciar la sesión desde un botón "nuevo trámite" en vez de esperar la detección automática.

Comportamientos erráticos:El usuario se mueve fuera del encuadre; hace la seña incompleta y se detiene; la traducción sugerida es incorrecta y la rechaza; hay solapamiento de manos y se pierde el seguimiento.

Cómo el diseño absorbe estos errores:Si la cámara pierde el seguimiento, el sistema muestra un indicador de "reencuadra tus manos" en vez de fallar sin decir algo. Si la sugerencia es incorrecta, el usuario la rechaza con una seña de "no" y el sistema ofrece 2 o 3 opciones más probables. Si hay solapamiento de manos, el sistema pide reintentar la seña con ambas manos separadas ya que es un problema técnico de detección.

*Flujo 2 - Seleccionar el trámite mediante seña(menú inicial)*





![alt text](image-1.png)





Ruta feliz: el usuario hace la seña del trámite (una de las 25–30 del vocabulario institucional del MVP), el sistema la reconoce al primer intento y el usuario confirma sin corregir nada.

Side doors: El usuario puede seleccionar el trámite tocando el ícono en pantalla en vez de hacer señas;el empleado también puede preseleccionar el trámite desde su propia pantalla si el alumno ya lo mencionó de otra forma (una cita agendada).

Comportamientos erráticos:El usuario hace una seña que no corresponde a ningún trámite del menú; se equivoca de seña y confirma un trámite incorrecto; se queda inmóvil sin saber qué seña usar.

Cómo el diseño absorbe estos errores:Si la seña no coincide con ningún trámite del menú, el sistema no fuerza una selección: muestra las opciones más cercanas o cae en el Flujo 3 (flujo de duda). Si el usuario confirma un trámite equivocado, hay un botón visible de "regresar al menú" en todo momento.

*Flujo 3 - Pedir ayuda cuando el alumno no sabe que tramite necesita(seña de duda)*





![alt text](image-2.png)





Ruta feliz: El usuario hace la seña de duda (parte del vocabulario institucional del MVP), elige el departamento correcto a la primera y encuentra el trámite que

buscaba en la información mostrada.

Side doors: Se llega aquí automáticamente si en el Flujo 2, la seña no corresponde a ningún trámite del menú.

Comportamientos erráticos:El usuario no sabe a qué departamento pertenece su trámite y se queda atorado en la selección.La información del departamento no resuelve su duda real;el usuario se frustra al no encontrar su trámite en ninguna

categoría.

Cómo el diseño absorbe estos errores:Si el usuario no logra ubicar su trámite en ningún departamento, el sistema lo regresa al Flujo 1 (traducción libre) para que se

comunique directamente con el empleado con sus propias señas.
