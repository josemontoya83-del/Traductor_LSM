// Textos de la grabación: frases cortas y directas (el español es segunda lengua para
// muchas personas sordas). Si existe un video en LSM con la misma explicación, se muestra arriba:
//   public/instrucciones/<video>.mp4   (lo graba el intérprete una sola vez)

export const PASOS = [
    { picto: "encuadre", texto: "Siéntate frente a la cámara. Que se vea tu cabeza, tus hombros y tu pecho." },
    { picto: "abajo", texto: "Pon las manos abajo y espera la cuenta: 3, 2, 1." },
    { picto: "sena", texto: "Cuando veas ¡AHORA!, haz la seña." },
    { picto: "listo", texto: "Al terminar, baja las manos. Se guarda solo." },
];

export const BLOQUES = {
    letra: {
        picto: "letras", titulo: "Letras del alfabeto",
        texto: "Haz la letra que aparece y déjala quieta 2 segundos. Si la letra tiene movimiento (como la J o la Z), hazla 3 veces.",
    },
    numero: {
        picto: "numeros", titulo: "Números",
        texto: "Haz el número que aparece y déjalo quieto 2 segundos.",
    },
    sena: {
        picto: "sena", titulo: "Señas",
        texto: "Haz la seña como la haces siempre, a tu ritmo normal. Si no conoces una seña, toca «No la conozco».",
    },
    deletreo: {
        picto: "letras", titulo: "Palabras deletreadas",
        texto: "Deletrea la palabra completa, letra por letra, a tu ritmo normal. Al terminar, baja la mano.",
    },
    negativo: {
        picto: "nosena", titulo: "Movimientos que NO son seña",
        texto: "Aquí NO hagas señas. Haz lo que dice la pantalla, por ejemplo rascarte o ver tu celular. Dura 6 segundos.",
    },
    respuesta: {
        picto: "frase", titulo: "Frases del empleado",
        texto: "Di en señas la frase completa, como si tú atendieras la ventanilla. Cuando termines, toca «Terminé».",
    },
};

export const ENCUADRE = {
    ok: "¡Perfecto! Te vemos bien.",
    sin_persona: "No te vemos. Siéntate frente a la cámara.",
    lejos: "Estás lejos. Acércate un poco.",
    cerca: "Estás muy cerca. Aléjate un poco.",
    cabeza: "No se ve tu cabeza. Aléjate un poco.",
};

// Problemas de una toma -> mensaje simple. Cada uno con su propio ícono de alerta.
export const AVISOS = {
    sin_mano: "No vimos tu mano levantada. Levanta la mano para hacer la seña.",
    poca_mano: "Casi no vimos tu mano. Revisa la luz o acércate un poco.",
    sin_hombros: "No te vimos bien. Siéntate frente a la cámara.",
    tiempo: "Se acabó el tiempo con la mano arriba. Al terminar, baja las manos.",
};

// Texto que va en los metadatos (para el equipo), igual que en la captura clásica.
export const AVISOS_EQUIPO = {
    sin_mano: "No se vio la mano levantada: ¿se hizo la seña?",
    poca_mano: "La mano se detectó poco (luz, fondo o mano fuera de cuadro)",
    sin_hombros: "Casi no se vieron los hombros (revisa el encuadre)",
    tiempo: "Se cortó por tiempo con la mano arriba",
};

export const ERRORES_CAMARA = {
    permiso: "El navegador no deja usar la cámara. Toca el candado junto a la dirección y permite la cámara.",
    camara: "No encontramos una cámara. Conéctala y toca Reintentar.",
    servidor: "No hay conexión con el programa. Revisa que la ventana negra del servidor siga abierta y toca Reintentar.",
    grabadora: "Este navegador no puede grabar video. Usa Google Chrome o Microsoft Edge.",
};
