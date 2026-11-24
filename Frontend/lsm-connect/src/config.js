// Dirección del backend. Se puede cambiar con la variable VITE_API_URL (archivo .env).
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WS = API.replace(/^http/, "ws");

// Parámetros de la URL:
//   (sin ?rol)        alumno y empleado en la misma pantalla (demo)
//   ?rol=estudiante   solo la pantalla del alumno (cámara)
//   ?rol=ventanilla   solo la pantalla del empleado
//   ?sala=otra        otra ventanilla (las dos pantallas deben usar la misma sala)
const params = new URLSearchParams(window.location.search);
const rol = params.get("rol");
export const VISTA = rol === "estudiante" || rol === "ventanilla" ? rol : "ambos";
export const SALA = params.get("sala") ?? "principal";

// Cámara: tamaño y calidad del frame que se manda al backend
export const FRAME_ANCHO = 640;
export const FRAME_ALTO = 480;
export const FRAME_CALIDAD = 0.7;
