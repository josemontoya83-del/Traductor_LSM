// Dirección del backend. Se puede cambiar con la variable VITE_API_URL (archivo .env).
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WS = API.replace(/^http/, "ws");

// Parámetros de la URL: ?rol=ventanilla (pantalla del empleado) y ?sala=otra
const params = new URLSearchParams(window.location.search);
export const ROL_URL = params.get("rol") === "ventanilla" ? "ventanilla" : "estudiante";
export const SALA = params.get("sala") ?? "principal";

// Cámara: tamaño y calidad del frame que se manda al backend
export const FRAME_ANCHO = 640;
export const FRAME_ALTO = 480;
export const FRAME_CALIDAD = 0.7;
