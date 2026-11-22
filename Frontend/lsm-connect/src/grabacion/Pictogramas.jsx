// Pictogramas de las instrucciones (SVG, sin depender de internet). Usan currentColor.
const P = { fill: "none", stroke: "currentColor", strokeWidth: 4, strokeLinecap: "round", strokeLinejoin: "round" };

function Svg({ titulo, children, tam = 120 }) {
    return (
        <svg viewBox="0 0 120 120" width={tam} height={tam} role="img" aria-label={titulo} {...P}>
            {children}
        </svg>
    );
}

const Cabeza = () => <circle cx="60" cy="32" r="12" />;
const Torso = () => <path d="M38 112 V72 a22 22 0 0 1 44 0 V112" />;
const BrazosAbajo = () => <><path d="M38 76 L30 110" /><path d="M82 76 L90 110" /></>;
// Mano abierta (4 dedos + pulgar), a la izquierda; las letras/números van a la derecha.
const Mano = () => (
    <>
        <path d="M30 64 V34 a6 6 0 0 1 12 0 V60" />
        <path d="M42 58 V24 a6 6 0 0 1 12 0 V58" />
        <path d="M54 58 V28 a6 6 0 0 1 12 0 V60" />
        <path d="M66 60 V40 a6 6 0 0 1 12 0 V78" />
        <path d="M30 64 V88 a22 22 0 0 0 22 22 H56 a22 22 0 0 0 22 -22 V78" />
        <path d="M30 80 L20 70 a6 6 0 0 0 -9 8 L30 100" />
    </>
);
const Letras = ({ a, b, c }) => (
    <g fill="currentColor" stroke="none" fontSize="20" fontWeight="700" textAnchor="middle">
        <text x="102" y="38">{a}</text><text x="102" y="68">{b}</text><text x="102" y="98">{c}</text>
    </g>
);

export function PictoEncuadre({ tam }) {
    return (
        <Svg titulo="Que se vea tu cabeza, hombros y pecho" tam={tam}>
            <path d="M8 30 V8 H30 M90 8 H112 V30 M112 90 V112 H90 M30 112 H8 V90" />
            <Cabeza /><Torso /><BrazosAbajo />
        </Svg>
    );
}

export function PictoManosAbajo({ tam }) {
    return (
        <Svg titulo="Manos abajo" tam={tam}>
            <Cabeza /><Torso /><BrazosAbajo />
            <path d="M106 58 V98 M98 90 L106 98 L114 90" />
        </Svg>
    );
}

export function PictoSena({ tam }) {
    return (
        <Svg titulo="Haz la seña" tam={tam}>
            <Cabeza /><Torso />
            <path d="M38 76 L30 110" />
            <path d="M82 76 L98 58 L94 38" />
            <circle cx="93" cy="31" r="6" />
            <path d="M104 20 a14 14 0 0 1 6 16" />
        </Svg>
    );
}

export function PictoListo({ tam }) {
    return (
        <Svg titulo="Baja las manos y se guarda solo" tam={tam}>
            <Cabeza /><Torso /><BrazosAbajo />
            <circle cx="96" cy="26" r="16" />
            <path d="M88 26 L94 32 L104 20" />
        </Svg>
    );
}

export function PictoLetras({ tam }) {
    return (
        <Svg titulo="Letras con la mano" tam={tam}>
            <Mano />
            <Letras a="A" b="B" c="C" />
        </Svg>
    );
}

export function PictoNumeros({ tam }) {
    return (
        <Svg titulo="Números con la mano" tam={tam}>
            <Mano />
            <Letras a="1" b="2" c="3" />
        </Svg>
    );
}

export function PictoNoSena({ tam }) {
    return (
        <Svg titulo="Movimiento que no es seña" tam={tam}>
            <Cabeza /><Torso />
            <path d="M38 76 L30 110" />
            <path d="M82 76 L94 52 L72 22" />
            <circle cx="22" cy="24" r="14" />
            <path d="M12 34 L32 14" />
        </Svg>
    );
}

export function PictoFrase({ tam }) {
    return (
        <Svg titulo="Frase completa en señas" tam={tam}>
            <Cabeza /><Torso />
            <path d="M38 76 L22 58 L26 38" /><circle cx="27" cy="31" r="6" />
            <path d="M82 76 L98 58 L94 38" /><circle cx="93" cy="31" r="6" />
        </Svg>
    );
}

// ---- íconos de botones (estilo Lucide, 24x24)
function Icono({ children, tam = 28 }) {
    return (
        <svg viewBox="0 0 24 24" width={tam} height={tam} aria-hidden="true" {...P} strokeWidth={2.5}>
            {children}
        </svg>
    );
}

export const IcoPausa = (p) => <Icono {...p}><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /></Icono>;
export const IcoSeguir = (p) => <Icono {...p}><polygon points="6 3 20 12 6 21 6 3" /></Icono>;
export const IcoRepetir = (p) => <Icono {...p}><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /></Icono>;
export const IcoSaltar = (p) => <Icono {...p}><polygon points="5 4 15 12 5 20 5 4" /><line x1="19" x2="19" y1="5" y2="19" /></Icono>;
export const IcoTermine = (p) => <Icono {...p}><rect x="5" y="5" width="14" height="14" rx="2" /></Icono>;
export const IcoBien = (p) => <Icono {...p}><path d="M20 6 9 17l-5-5" /></Icono>;
export const IcoAlerta = (p) => <Icono {...p}><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /><path d="M12 9v4" /><path d="M12 17h.01" /></Icono>;
