import { API } from "../config.js";

async function pedir(ruta, opciones) {
    let r;
    try {
        r = await fetch(`${API}${ruta}`, opciones);
    } catch {
        throw new Error("No hay conexión con el programa. Revisa que la ventana negra del servidor siga abierta.");
    }
    const datos = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof datos.detail === "string" ? datos.detail : "El servidor no pudo hacerlo. Intenta de nuevo.");
    return datos;
}

export function obtenerProtocolo() {
    return pedir("/grabacion/protocolo");
}

export function obtenerEstado(persona, sesion, { opcionales = false, bloques = "" } = {}) {
    const q = new URLSearchParams({ persona, sesion, opcionales: String(opcionales), bloques });
    return pedir(`/grabacion/estado?${q}`);
}

export function registrarPersona(datos) {
    return pedir("/grabacion/persona", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
    });
}

export function subirToma({ persona, sesion, nombre, blob, meta }) {
    const f = new FormData();
    f.append("persona", persona);
    f.append("sesion", sesion);
    f.append("nombre", nombre);
    f.append("meta", JSON.stringify(meta));
    f.append("video", blob, `${nombre}.${blob.type.includes("mp4") ? "mp4" : "webm"}`);
    return pedir("/grabacion/toma", { method: "POST", body: f });
}

export function borrarToma(persona, sesion, nombre) {
    const q = new URLSearchParams({ persona, sesion, nombre });
    return pedir(`/grabacion/toma?${q}`, { method: "DELETE" });
}
