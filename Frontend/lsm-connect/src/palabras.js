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

// Las 14 palabras que el modelo reconoce (en el orden en que se muestran).
export const PALABRAS = Object.keys(BONITAS);
// De ellas, las que son un trámite (para la etiqueta del panel del empleado).
export const TRAMITES_CLAVE = ["inscripcion", "reinscripcion", "kardex", "constancia", "credencial", "documentos"];