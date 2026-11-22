// Dirección del backend. Se puede cambiar con la variable VITE_API_URL (archivo .env).
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WS = API.replace(/^http/, "ws");

// Parámetros de la URL:
//   ?dominio=escolar      paquete de vocabulario de esta ventanilla (varios: escolar,caja)
//   ?ventanilla=2         número que se muestra en el encabezado
const params = new URLSearchParams(window.location.search);
export const DOMINIOS = (params.get("dominio") ?? "escolar").split(",").filter(Boolean);
export const VENTANILLA = params.get("ventanilla") ?? "1";

// Cámara: tamaño y calidad del frame que se manda al backend
export const FRAME_ANCHO = 640;
export const FRAME_ALTO = 480;
export const FRAME_CALIDAD = 0.7;
