# P2: Empathy Map Parser & Prototipo de Interfaz (LSM Escolar)

Esta parte del repositorio contiene la implementación técnica de dos herramientas clave para la investigación y diseño de la plataforma de Traducción de Lengua de Señas Mexicana (LSM) a Texto en entornos educativos: un **Empathy Map Interactivo ("The Parser")** y un **Prototipo Navegable** basado en algoritmos de atención.

---

## Parte 1: Empathy Map Parser (`index.html`)

Una herramienta funcional diseñada para procesar datos cualitativos de usuarios en campo (incluyendo usuarios extremos y expertos) y generar insights accionables.

### Características Implementadas:
* **Estructura Visual:** Cuadrícula 2x2 interactiva (Dice, Piensa, Hace, Siente) y una "bandeja de ruido cualitativo" de entrada.
* **Operaciones CRUD:** 
  * **Crear:** Formulario integrado para inyectar nuevas observaciones.
  * **Leer & Actualizar:** Sistema Drag & Drop para categorizar tarjetas y controles de rango para medir la intensidad (1-5) en el cuadrante "Siente".
  * **Borrar:** Eliminación individual de tarjetas.
* **Persistencia de Datos:** Uso de `localStorage` para guardar el estado del tablero y la posición de cada tarjeta entre recargas de página.
* **Algoritmo de Insights:** Generador heurístico dinámico que analiza palabras clave e intensidad emocional de las tarjetas activas para determinar la prioridad (Alta/Media/Baja) y el tipo de fricción detectada.
* **Exportación:** Botones para descargar los datos procesados en formatos `.json` y `.csv`.

---

## Parte 2: Algoritmos de Atención y Prototipo (`prototipo.html`)

Implementación de wireframes navegables aplicando técnicas de jerarquía visual para optimizar la carga cognitiva de los usuarios (alumnos y maestros).

### Documentación de Wireframes (3 Capas)
![Wireframes del Prototipo](wireframes.png)
**WF1: Pantalla de Inicio (Trámite Pendiente)**
* **Capa Base (Estructura):** Implementación estricta de la "Pirámide Invertida". El bloque amarillo superior funciona como un **Johnson Box** que aísla el mensaje crítico ("Tienes un tramite pendiente"). La navegación global se ancla en el tercio inferior.
* **Capa Media (Contenido):** Gráfico central que representa al usuario. Un CTA claro y centrado ("Iniciar Traducción") con iconografía de apoyo (pulgar arriba) para un escaneo visual rápido.
* **Capa Superior (Estado):** El sistema indica un estado de "tarea incompleta" y ofrece una salida contextual rápida ("Ir a recordatorios").

**WF2: Pantalla de Tarea Principal (Traducción en Proceso)**
* **Capa Base (Estructura):** Se mantiene el Johnson Box para dar contexto continuo sobre la meta ("Mañana hay que traer una constancia"). El área central se reserva para el flujo de la tarea principal.
* **Capa Media (Contenido):** Controles de acción posteriores a la tarea: "Guardar en historial", "Verificar traducción" y "Repetir traducción".
* **Capa Superior (Estado):** Retroalimentación de sistema en tiempo real ("Traducción en proceso...") complementada con métricas que reducen la incertidumbre técnica ("Confiabilidad: 96%", "Velocidad: Perfecta").

### Rutas del Prototipo (SPA Enrutada)
El prototipo funciona como una Single Page Application con las siguientes rutas enlazadas por hash (`#/ruta`):
* `/` - Pantalla de inicio (WF1).
* `/sesion/:id` - Pantalla de la tarea principal de traducción (WF2) [Flujo principal completado].
* `/buscar` - Buscador global de tutores/traducciones.
* `/tutor/:id` - Perfil específico del tutor o maestro.
* `/agendar/:tutorId` - Flujo para agendar una sesión.
* `/sesiones` - Historial de tareas y traducciones.

---

## 🚀 Cómo ejecutar el proyecto

1. Clona este repositorio.
2. Abre el archivo `index.html` en cualquier navegador moderno para utilizar el Empathy Map.
3. Abre el archivo `prototipo.html` en el navegador (preferentemente usando la vista de herramientas de desarrollador en modo móvil) para navegar por el flujo de tareas. No se requieren dependencias de servidor (Node.js/NPM), todo funciona mediante Vanilla JS y Tailwind CSS vía CDN.