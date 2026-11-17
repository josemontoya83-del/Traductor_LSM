// El modelo responde con nombres sin acento. Aquí se convierten a como se leen en pantalla.
const BONITAS = {
    inscripcion: "Inscripción",
    reinscripcion: "Reinscripción",
    kardex: "Kárdex",
    constancia: "Constancia",
    foto: "Foto",
    credencial: "Credencial",
    documentos: "Documentos",
    solicitar: "Solicitar",
    recoger: "Recoger",
    entrega: "Entrega",
    si: "Sí",
    no: "No",
    duda: "Tengo una duda",
    gracias: "Gracias",
};

export function bonita(palabra) {
    return BONITAS[palabra] ?? palabra.charAt(0).toUpperCase() + palabra.slice(1);
}

// Lista de RESPALDO: la lista real la manda el servidor (GET /clases), que la lee del modelo
// entrenado. Esta solo se usa si el servidor no responde. Si se agrega una palabra al modelo,
// basta con ponerle aquí su forma con acentos (si no, se muestra con mayúscula inicial).
export const PALABRAS = Object.keys(BONITAS);
// Las que son un trámite (para la etiqueta del panel del empleado).
export const TRAMITES_CLAVE = ["inscripcion", "reinscripcion", "kardex", "constancia", "credencial", "documentos", "beca"];