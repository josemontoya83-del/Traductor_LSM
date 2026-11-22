import React, { useEffect, useRef, useState } from "react";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "./grabacion.css";
import { borrarToma, obtenerEstado, obtenerProtocolo, registrarPersona, subirToma } from "./api.js";
import { useCamaraGrabacion } from "./useCamaraGrabacion.js";
import * as Pic from "./Pictogramas.jsx";
import { AVISOS, AVISOS_EQUIPO, BLOQUES, ENCUADRE, ERRORES_CAMARA, PASOS } from "./textos.js";

/*
 * Grabación en autoservicio (http://localhost:5173/grabar).
 *   1. El EQUIPO escribe el código de la persona y la sesión (y la registra la primera vez).
 *   2. La PERSONA SORDA sigue sola: instrucciones -> revisar cámara -> práctica -> bloques.
 *      Cada toma empieza sola cuando tiene las manos abajo y termina sola al bajarlas.
 */

const CUENTA_S = 3;                 // cuenta regresiva (se graba desde aquí: reposo antes de la seña)
const LECTURA_S = { letra: 2, numero: 2, sena: 2.5, deletreo: 3, negativo: 3.5, respuesta: 4 };
const REPOSO_PARA_EMPEZAR_MS = 1000;
const PAUSA_FIN_MS = 800;           // manos abajo después de firmar -> termina la toma
const MIN_ACTIVO_MS = 300;
const SEG_POR_TOMA = 8;             // para estimar el tiempo restante

const PRACTICA = [
    { nombre: "practica_hola", bloque: "P", nombre_bloque: "Práctica", tipo: "sena", etiqueta: "hola", texto: "Hola",
      instruccion: "Haz la seña", segundos_max: 6, parar_al_bajar: true, pista: "" },
    { nombre: "practica_a", bloque: "P", nombre_bloque: "Práctica", tipo: "letra", etiqueta: "a", texto: "A",
      instruccion: "Sostén la letra", segundos_max: 4, parar_al_bajar: true, pista: "" },
];

const PICTOS = {
    encuadre: Pic.PictoEncuadre, abajo: Pic.PictoManosAbajo, sena: Pic.PictoSena, listo: Pic.PictoListo,
    letras: Pic.PictoLetras, numeros: Pic.PictoNumeros, nosena: Pic.PictoNoSena, frase: Pic.PictoFrase,
};

function Picto({ nombre, tam = 120 }) {
    const C = PICTOS[nombre] ?? Pic.PictoSena;
    return <span className="g-picto"><C tam={tam} /></span>;
}

/** Video de ayuda en LSM: solo aparece si el archivo existe en public/. */
function VideoAyuda({ src, etiqueta }) {
    const [ok, setOk] = useState(true);
    if (!ok) return null;
    return (
        <video className="g-video-ayuda" src={src} autoPlay loop muted playsInline controls
            onError={() => setOk(false)} aria-label={etiqueta} />
    );
}

function minutos(n) {
    return Math.max(1, Math.round((n * SEG_POR_TOMA) / 60));
}

// =====================================================================================
export default function Grabacion() {
    const [pantalla, setPantalla] = useState("equipo"); // equipo | instrucciones | encuadre | practica | toma | bloque | fin
    const [sesion, setSesion] = useState(null);         // { persona, sesion, pendientes, total, hechas }
    const [indice, setIndice] = useState(0);
    const [intento, setIntento] = useState(0);
    const [historial, setHistorial] = useState([]);     // índices guardados en esta visita (para "Repetir la anterior")
    const [saltadas, setSaltadas] = useState([]);
    const [practicar, setPracticar] = useState(true);
    const [iPractica, setIPractica] = useState(0);
    const [bloqueAnterior, setBloqueAnterior] = useState(null);
    const [completa, setCompleta] = useState(false);     // llegó al final de la lista
    const camara = useCamaraGrabacion(pantalla !== "equipo" && pantalla !== "fin");

    const toma = sesion?.pendientes[indice];

    function empezar(datos, conPractica) {
        setSesion(datos);
        setIndice(0);
        setHistorial([]);
        setSaltadas([]);
        setPracticar(conPractica);
        setBloqueAnterior(null);
        setCompleta(!datos.pendientes.length);
        setPantalla(datos.pendientes.length ? "instrucciones" : "fin");
    }

    function despuesDeEncuadre() {
        if (practicar) {
            setIPractica(0);
            setPantalla("practica_intro");
        } else {
            setPantalla("bloque");
        }
    }

    function avanzar(guardada) {
        if (guardada) setHistorial((h) => [...h, indice]);
        const siguiente = indice + 1;
        setIntento(0);
        if (siguiente >= sesion.pendientes.length) {
            setCompleta(true);
            setPantalla("fin");
            return;
        }
        setIndice(siguiente);
        if (sesion.pendientes[siguiente].bloque !== toma.bloque) {
            setBloqueAnterior(toma.nombre_bloque);
            setPantalla("bloque");
        }
    }

    async function repetirAnterior() {
        const previo = historial[historial.length - 1];
        if (previo === undefined) return;
        await borrarToma(sesion.persona, sesion.sesion, sesion.pendientes[previo].nombre).catch(() => {});
        setHistorial((h) => h.slice(0, -1));
        setIndice(previo);
        setIntento((n) => n + 1);
    }

    function saltar() {
        setSaltadas((s) => [...s, toma]);
        avanzar(false);
    }

    function reintentarSaltadas() {
        setSesion((s) => ({ ...s, pendientes: saltadas }));
        setSaltadas([]);
        setHistorial([]);
        setIndice(0);
        setBloqueAnterior(null);
        setCompleta(false);
        setPantalla("bloque");
    }

    if (pantalla === "equipo") return <PantallaEquipo onEmpezar={empezar} />;

    const errorCamara = camara.error && (
        <div className="g-error" role="alert">
            <Pic.IcoAlerta tam={40} />
            <p>{ERRORES_CAMARA[camara.error]}</p>
            <button className="g-btn g-btn--primario" onClick={camara.reintentar}>Reintentar</button>
        </div>
    );

    if (pantalla === "instrucciones") {
        return (
            <Marco>
                <h1 className="g-titulo">Así se graba</h1>
                <VideoAyuda src="/instrucciones/bienvenida.mp4" etiqueta="Instrucciones en LSM" />
                <ol className="g-pasos">
                    {PASOS.map((p, i) => (
                        <li key={i} className="g-paso">
                            <span className="g-paso__num" aria-hidden="true">{i + 1}</span>
                            <Picto nombre={p.picto} tam={110} />
                            <p>{p.texto}</p>
                        </li>
                    ))}
                </ol>
                <ul className="g-ayudas">
                    <li><Pic.IcoRepetir /> Si te equivocas, toca <strong>Repetir</strong>.</li>
                    <li><Pic.IcoPausa /> Si te cansas, toca <strong>Pausa</strong>.</li>
                    <li><Pic.IcoSaltar /> Si no conoces una seña, toca <strong>No la conozco</strong>.</li>
                </ul>
                <button className="g-btn g-btn--primario g-btn--grande" onClick={() => setPantalla("encuadre")} autoFocus>
                    Entendí <Pic.IcoSeguir />
                </button>
            </Marco>
        );
    }

    if (pantalla === "encuadre") {
        const ok = camara.revision.encuadre === "ok";
        return (
            <Marco>
                <h1 className="g-titulo">Revisa la cámara</h1>
                {errorCamara}
                <div className={`g-camara g-camara--encuadre ${ok ? "es-ok" : ""}`}>
                    <video ref={camara.conectarVideo} muted playsInline aria-label="Tu imagen en la cámara" />
                    <svg className="g-silueta" viewBox="0 0 160 120" aria-hidden="true">
                        <circle cx="80" cy="38" r="15" /><path d="M44 120 V92 a36 36 0 0 1 72 0 V120" />
                    </svg>
                    <Estado ok={ok} texto={ENCUADRE[camara.revision.encuadre]} />
                </div>
                <p className="g-nota">Pon tu cuerpo dentro de la figura. Busca luz de frente, no una ventana detrás de ti.</p>
                <button className={`g-btn g-btn--grande ${ok ? "g-btn--primario" : ""}`} onClick={despuesDeEncuadre}>
                    {ok ? "Seguir" : "Seguir de todos modos"} <Pic.IcoSeguir />
                </button>
            </Marco>
        );
    }

    if (pantalla === "practica_intro") {
        return (
            <Marco>
                <Picto nombre="sena" tam={140} />
                <h1 className="g-titulo">Vamos a practicar</h1>
                <p className="g-texto">Primero 2 pruebas para que veas cómo funciona. <strong>No se guardan.</strong></p>
                <button className="g-btn g-btn--primario g-btn--grande" autoFocus onClick={() => setPantalla("practica")}>
                    Practicar <Pic.IcoSeguir />
                </button>
            </Marco>
        );
    }

    if (pantalla === "practica") {
        if (iPractica >= PRACTICA.length) {
            return (
                <Marco>
                    <span className="g-sello g-sello--ok"><Pic.IcoBien tam={56} /></span>
                    <h1 className="g-titulo">¡Muy bien! Ya sabes cómo.</h1>
                    <p className="g-texto">Ahora empieza la grabación de verdad.</p>
                    <div className="g-fila">
                        <button className="g-btn g-btn--grande" onClick={() => setIPractica(0)}>
                            <Pic.IcoRepetir /> Practicar otra vez
                        </button>
                        <button className="g-btn g-btn--primario g-btn--grande" autoFocus onClick={() => setPantalla("bloque")}>
                            Empezar <Pic.IcoSeguir />
                        </button>
                    </div>
                </Marco>
            );
        }
        return (
            <Toma key={`p${iPractica}`} toma={PRACTICA[iPractica]} camara={camara} practica errorCamara={errorCamara}
                progreso={{ n: iPractica + 1, total: PRACTICA.length, etiqueta: "Práctica (no se guarda)" }}
                onSiguiente={() => setIPractica((i) => i + 1)} />
        );
    }

    if (pantalla === "bloque" && toma) {
        const b = BLOQUES[toma.tipo];
        const restantes = sesion.pendientes.slice(indice).filter((t) => t.bloque === toma.bloque).length;
        return (
            <Marco>
                {bloqueAnterior && (
                    <p className="g-felicita"><Pic.IcoBien /> ¡Terminaste «{bloqueAnterior}»! Descansa un momento.</p>
                )}
                <Picto nombre={b.picto} tam={140} />
                <h1 className="g-titulo">{b.titulo}</h1>
                <VideoAyuda src={`/instrucciones/bloque_${toma.bloque}.mp4`} etiqueta={`Explicación en LSM: ${b.titulo}`} />
                <p className="g-texto">{b.texto}</p>
                <p className="g-nota">{restantes} {restantes === 1 ? "toma" : "tomas"} · unos {minutos(restantes)} minutos</p>
                <button className="g-btn g-btn--primario g-btn--grande" autoFocus onClick={() => setPantalla("toma")}>
                    Empezar <Pic.IcoSeguir />
                </button>
            </Marco>
        );
    }

    if (pantalla === "toma" && toma) {
        const n = sesion.hechas + historial.length + 1;
        return (
            <Toma key={`${toma.nombre}-${intento}`} toma={toma} camara={camara} errorCamara={errorCamara}
                persona={sesion.persona} sesion={sesion.sesion}
                progreso={{ n: Math.min(n, sesion.total), total: sesion.total, etiqueta: toma.nombre_bloque }}
                onSiguiente={avanzar} onSaltar={saltar}
                onRepetirAnterior={historial.length ? repetirAnterior : null}
                onTerminarHoy={() => setPantalla("fin")} />
        );
    }

    // fin
    return (
        <Marco>
            <span className="g-sello g-sello--ok"><Pic.IcoBien tam={56} /></span>
            <h1 className="g-titulo">{completa ? "¡Terminaste la sesión!" : "Listo por hoy"}</h1>
            <p className="g-texto">Gracias por tu ayuda. Todo lo que grabaste ya está guardado.</p>
            {!completa && (
                <p className="g-nota">Para seguir otro día, el equipo escribe el mismo código y la misma sesión: empieza donde te quedaste.</p>
            )}
            {saltadas.length > 0 && (
                <div className="g-fila">
                    <p className="g-nota">Saltaste {saltadas.length} {saltadas.length === 1 ? "seña" : "señas"}.</p>
                    <button className="g-btn" onClick={reintentarSaltadas}><Pic.IcoRepetir /> Intentar las que salté</button>
                </div>
            )}
            <button className="g-btn g-btn--grande" onClick={() => { setSesion(null); setPantalla("equipo"); }}>
                Volver al inicio (equipo)
            </button>
        </Marco>
    );
}

function Marco({ children }) {
    return (
        <div className="g-app">
            <main className="g-marco">{children}</main>
        </div>
    );
}

function Estado({ ok, texto, tipo }) {
    return (
        <p className={`g-estado ${ok ? "g-estado--ok" : ""} ${tipo ? `g-estado--${tipo}` : ""}`} role="status" aria-live="polite">
            {ok ? <Pic.IcoBien /> : <Pic.IcoAlerta />} <span>{texto}</span>
        </p>
    );
}

// =====================================================================================
// Una toma: preparar -> cuenta (graba) -> grabando -> guardando -> bien | revisar
function Toma({ toma, camara, practica = false, persona, sesion, progreso, errorCamara,
                onSiguiente, onSaltar, onRepetirAnterior, onTerminarHoy }) {
    const [fase, setFase] = useState("preparar");
    const [pausa, setPausa] = useState(false);
    const [mensaje, setMensaje] = useState(null);
    const [avisos, setAvisos] = useState([]);
    const [ahora, setAhora] = useState(performance.now());
    const reg = useRef(null);
    const faseRef = useRef(fase);
    const pausaRef = useRef(pausa);
    const pendienteRef = useRef(null);  // { blob, meta } si falló la subida
    // El objeto `camara` y los callbacks del padre cambian en cada render (la revisión llega
    // ~10 veces por segundo): se leen siempre desde refs para no reiniciar relojes ni grabaciones.
    const cam = useRef(camara);
    const sigRef = useRef(onSiguiente);
    const terminarRef = useRef(null);
    faseRef.current = fase;
    pausaRef.current = pausa;
    cam.current = camara;
    sigRef.current = onSiguiente;

    function reiniciarRegistro() {
        reg.current = { inicio: performance.now(), reposoDesde: null, activoEnCuenta: null, ultimaRev: 0,
                        primera: null, ultima: null, analizados: 0, mano: 0, hombros: 0, activos: 0,
                        tramo: 0, tramoUltima: 0 };
    }
    if (reg.current === null) reiniciarRegistro();

    function cambiarFase(f) {
        reg.current.inicio = performance.now();
        faseRef.current = f;
        setFase(f);
        cam.current.fase(f);
    }

    async function terminar(motivo) {
        if (faseRef.current !== "grabando") return;
        cambiarFase("guardando");
        const camara = cam.current;
        const r = await camara.detenerGrabacion();
        const g = reg.current;
        const n = Math.max(g.analizados, 1);
        const codigos = [];
        if (g.hombros / n < 0.7) codigos.push("sin_hombros");
        if (toma.tipo !== "negativo") {
            if (g.activos === 0) codigos.push("sin_mano");
            // dentro del tramo en que firmó, ¿en cuántos cuadros se vio la mano levantada?
            else if (g.activos / Math.max(g.tramoUltima, 1) < 0.5) codigos.push("poca_mano");
            if (motivo === "tiempo" && toma.parar_al_bajar && g.ultima && performance.now() - g.ultima < 300) codigos.push("tiempo");
        }
        setAvisos(codigos);
        if (!r || !r.blob.size) {
            setMensaje("No se pudo grabar el video. Toca Repetir.");
            setFase("revisar");
            return;
        }
        if (!practica) {
            const meta = {
                duracion_s: Math.round(r.duracion * 1000) / 1000, motivo_fin: motivo,
                ancho: camara.ajustes?.ancho, alto: camara.ajustes?.alto, fps_camara: camara.ajustes?.fps,
                navegador: navigator.userAgent,
                calidad: { deteccion_mano: +(g.mano / n).toFixed(3), deteccion_hombros: +(g.hombros / n).toFixed(3),
                           cuadros_activos: g.activos, avisos: codigos.map((c) => AVISOS_EQUIPO[c]) },
            };
            pendienteRef.current = { blob: r.blob, meta };
            try {
                await subirToma({ persona, sesion, nombre: toma.nombre, blob: r.blob, meta });
                pendienteRef.current = null;
            } catch (e) {
                setMensaje(e.message);
                setFase("error");
                return;
            }
        }
        setFase(codigos.length ? "revisar" : "bien");
    }
    terminarRef.current = terminar;

    async function reintentarSubida() {
        const p = pendienteRef.current;
        if (!p) return;
        try {
            await subirToma({ persona, sesion, nombre: toma.nombre, blob: p.blob, meta: p.meta });
            pendienteRef.current = null;
            setMensaje(null);
            setFase(avisos.length ? "revisar" : "bien");
        } catch (e) {
            setMensaje(e.message);
        }
    }

    function repetir() {
        setAvisos([]);
        setMensaje(null);
        reiniciarRegistro();
        cambiarFase("preparar");
    }

    function pausar() {
        if (faseRef.current === "cuenta") {
            cam.current.cancelarGrabacion();
            cambiarFase("preparar");
        }
        if (faseRef.current === "preparar") {
            pausaRef.current = true;
            setPausa(true);
        }
    }

    function seguir() {
        pausaRef.current = false;
        setPausa(false);
        reiniciarRegistro();
        cambiarFase("preparar");
    }

    // ---- reloj de la toma
    useEffect(() => {
        const id = setInterval(() => {
            const t = performance.now();
            setAhora(t);
            if (pausaRef.current) return;
            const g = reg.current;
            const camara = cam.current;
            const rev = camara.revRef.current;
            const fresca = t - rev.t < 1500;
            const nueva = rev.t !== g.ultimaRev;
            g.ultimaRev = rev.t;
            const f = faseRef.current;

            if ((f === "cuenta" || f === "grabando") && nueva) {
                g.analizados += 1;
                g.mano += rev.mano ? 1 : 0;
                g.hombros += rev.hombros ? 1 : 0;
                if (f === "grabando" && (rev.activa || g.primera)) g.tramo += 1;
                if (f === "grabando" && rev.activa) {
                    g.activos += 1;
                    g.primera = g.primera ?? t;
                    g.ultima = t;
                    g.tramoUltima = g.tramo;
                }
            }

            if (f === "preparar") {
                const listo = fresca && rev.encuadre === "ok" && !rev.activa;
                g.reposoDesde = listo ? (g.reposoDesde ?? t) : null;
                const leyo = t - g.inicio >= (LECTURA_S[toma.tipo] ?? 2.5) * 1000;
                if (leyo && g.reposoDesde && t - g.reposoDesde >= REPOSO_PARA_EMPEZAR_MS) {
                    if (camara.iniciarGrabacion()) {
                        setMensaje(null);
                        g.analizados = g.mano = g.hombros = g.activos = g.tramo = g.tramoUltima = 0;
                        g.primera = g.ultima = g.activoEnCuenta = null;
                        cambiarFase("cuenta");
                    }
                }
            } else if (f === "cuenta") {
                g.activoEnCuenta = fresca && rev.activa ? (g.activoEnCuenta ?? t) : null;
                if (g.activoEnCuenta && t - g.activoEnCuenta > 400) {
                    camara.cancelarGrabacion();
                    setMensaje("Espera a que termine la cuenta. Empieza cuando veas ¡AHORA!");
                    g.reposoDesde = null;
                    cambiarFase("preparar");
                    g.inicio = t - 1500;   // no hace falta volver a leer toda la palabra
                } else if (t - g.inicio >= CUENTA_S * 1000) {
                    cambiarFase("grabando");
                }
            } else if (f === "grabando") {
                if (t - g.inicio >= toma.segundos_max * 1000) terminarRef.current("tiempo");
                else if (toma.parar_al_bajar && g.primera && g.ultima - g.primera >= MIN_ACTIVO_MS
                         && t - g.ultima >= PAUSA_FIN_MS) terminarRef.current("manos_abajo");
            }
        }, 100);
        return () => clearInterval(id);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // "¡Bien!" un momento y a la siguiente
    useEffect(() => {
        if (fase !== "bien") return;
        const id = setTimeout(() => sigRef.current(true), 1100);
        return () => clearTimeout(id);
    }, [fase]);

    // Si se desmonta grabando (p. ej. "Terminar por hoy"), no dejar la grabadora encendida.
    useEffect(() => () => cam.current.cancelarGrabacion(), []);

    // Teclado: ESPACIO = pausa/seguir (o "Terminé" mientras graba), R = repetir la anterior
    useEffect(() => {
        function tecla(e) {
            if (e.target.tagName === "INPUT" || e.repeat) return;
            if (e.key === " ") {
                e.preventDefault();   // también evita que ESPACIO "presione" el botón enfocado
                if (faseRef.current === "grabando") terminar("persona");
                else if (pausaRef.current) seguir();
                else pausar();
            } else if ((e.key === "r" || e.key === "R") && faseRef.current === "preparar" && onRepetirAnterior) {
                onRepetirAnterior();
            }
        }
        window.addEventListener("keydown", tecla);
        return () => window.removeEventListener("keydown", tecla);
    });

    // ---- textos de estado
    const rev = camara.revision;
    const g = reg.current;
    const transcurrido = (ahora - g.inicio) / 1000;
    let estado = { ok: false, texto: "" };
    if (fase === "preparar") {
        if (rev.encuadre !== "ok") estado = { ok: false, texto: ENCUADRE[rev.encuadre] };
        else if (rev.activa) estado = { ok: false, texto: "Baja las manos para empezar." };
        else estado = { ok: true, texto: "Manos abajo. Ya casi empieza…" };
    } else if (fase === "cuenta") estado = { ok: true, texto: "Manos abajo. Espera ¡AHORA!" };
    else if (fase === "grabando") {
        estado = { ok: true, tipo: "grabando",
                   texto: toma.tipo === "negativo" ? "Sigue con el movimiento…"
                        : toma.parar_al_bajar ? "Al terminar, baja las manos." : "Al terminar, toca «Terminé»." };
    } else if (fase === "guardando") estado = { ok: true, texto: "Guardando…" };

    const cuenta = Math.max(1, Math.ceil(CUENTA_S - transcurrido));
    const pct = Math.min(100, ((progreso.n - 1) / progreso.total) * 100);   // tomas YA hechas

    return (
        <div className="g-app">
            <header className="g-progreso">
                <span className="g-progreso__bloque">{progreso.etiqueta}</span>
                <span className="g-progreso__num">{progreso.n} de {progreso.total}</span>
                <div className="g-barra" role="progressbar" aria-valuemin={0} aria-valuemax={progreso.total}
                    aria-valuenow={progreso.n} aria-label="Avance"><span style={{ width: `${pct}%` }} /></div>
            </header>

            <main className="g-toma">
                <section className="g-tarjeta" aria-live="polite">
                    <p className="g-instruccion"><Picto nombre={BLOQUES[toma.tipo]?.picto} tam={44} /> {toma.instruccion}</p>
                    <p className={`g-palabra ${toma.texto.length > 12 ? "g-palabra--larga" : ""}`}>{toma.texto}</p>
                    {toma.pista && <p className="g-pista">{toma.pista}</p>}
                    {!practica && (
                        <VideoAyuda key={toma.nombre} src={`/ejemplos/${toma.tipo}_${toma.etiqueta}.mp4`}
                            etiqueta={`Ejemplo en LSM: ${toma.texto}`} />
                    )}
                </section>

                <section className={`g-camara g-camara--${fase}`}>
                    <video ref={camara.conectarVideo} muted playsInline aria-label="Tu imagen en la cámara" />
                    {fase === "grabando" && <span className="g-rec"><span className="g-rec__punto" /> GRABANDO</span>}
                    {fase === "cuenta" && <span className="g-cuenta" aria-live="assertive">{cuenta}</span>}
                    {fase === "grabando" && transcurrido < 1 && <span className="g-ahora">¡AHORA!</span>}
                    {fase === "grabando" && (
                        <div className="g-tiempo" aria-hidden="true">
                            <span style={{ width: `${Math.min(100, (transcurrido / toma.segundos_max) * 100)}%` }} />
                        </div>
                    )}
                    {fase === "bien" && <span className="g-sello g-sello--ok g-sello--sobre"><Pic.IcoBien tam={72} /> ¡Bien!</span>}
                    {estado.texto && <Estado {...estado} />}
                </section>
            </main>

            {errorCamara}
            {mensaje && fase !== "error" && <p className="g-mensaje" role="alert"><Pic.IcoAlerta /> {mensaje}</p>}

            {fase === "revisar" && (
                <div className="g-revisar" role="alertdialog" aria-label="Hay que revisar esta toma">
                    <ul>
                        {avisos.map((c) => <li key={c}><Pic.IcoAlerta /> {AVISOS[c]}</li>)}
                    </ul>
                    <div className="g-fila">
                        <button className="g-btn g-btn--primario g-btn--grande" autoFocus onClick={repetir}>
                            <Pic.IcoRepetir /> Repetir
                        </button>
                        <button className="g-btn g-btn--grande" onClick={() => onSiguiente(!practica)}>
                            Seguir así <Pic.IcoSeguir />
                        </button>
                    </div>
                </div>
            )}

            {fase === "error" && (
                <div className="g-revisar" role="alertdialog" aria-label="No se pudo guardar">
                    <p><Pic.IcoAlerta /> {mensaje}</p>
                    <div className="g-fila">
                        <button className="g-btn g-btn--primario g-btn--grande" autoFocus onClick={reintentarSubida}>
                            <Pic.IcoRepetir /> Intentar guardar otra vez
                        </button>
                        <button className="g-btn g-btn--grande" onClick={repetir}>Grabar otra vez</button>
                    </div>
                </div>
            )}

            <footer className="g-acciones">
                {fase === "grabando" ? (
                    <button className="g-btn g-btn--grande g-btn--primario" onClick={() => terminar("persona")}>
                        <Pic.IcoTermine /> Terminé
                    </button>
                ) : (
                    <button className="g-btn g-btn--grande" onClick={pausar} disabled={fase !== "preparar" && fase !== "cuenta"}>
                        <Pic.IcoPausa /> Pausa
                    </button>
                )}
                {onRepetirAnterior && (
                    <button className="g-btn g-btn--grande" onClick={onRepetirAnterior} disabled={fase !== "preparar"}>
                        <Pic.IcoRepetir /> Repetir la anterior
                    </button>
                )}
                {onSaltar && toma.tipo === "sena" && (
                    <button className="g-btn g-btn--grande" onClick={onSaltar} disabled={fase !== "preparar"}>
                        <Pic.IcoSaltar /> No la conozco
                    </button>
                )}
            </footer>

            {pausa && (
                <div className="g-pausa" role="dialog" aria-modal="true" aria-label="En pausa">
                    <div className="g-pausa__caja">
                        <Pic.IcoPausa tam={64} />
                        <h2 className="g-titulo">En pausa</h2>
                        <p className="g-texto">Descansa. Cuando quieras, toca Seguir.</p>
                        <div className="g-fila">
                            <button className="g-btn g-btn--primario g-btn--grande" autoFocus onClick={seguir}>
                                <Pic.IcoSeguir /> Seguir
                            </button>
                            {onTerminarHoy && (
                                <button className="g-btn g-btn--grande" onClick={onTerminarHoy}>Terminar por hoy</button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// =====================================================================================
// Pantalla del equipo: código, sesión y registro (una vez por persona)
function PantallaEquipo({ onEmpezar }) {
    const [protocolo, setProtocolo] = useState(null);
    const [persona, setPersona] = useState("");
    const [sesion, setSesion] = useState("1");
    const [soloG, setSoloG] = useState(false);
    const [estado, setEstado] = useState(null);
    const [error, setError] = useState(null);
    const [registro, setRegistro] = useState({ mano_dominante: "", rango_edad: "", lsm_lengua_materna: null,
                                               anos_usando_lsm: "", region: "", notas: "", consentimiento: false });
    const [practicar, setPracticar] = useState(true);

    useEffect(() => {
        obtenerProtocolo().then(setProtocolo).catch((e) => setError(e.message));
    }, []);

    const codigo = persona.trim().toUpperCase();
    const codigoValido = /^P\d{2,3}$/.test(codigo);

    async function consultar(e) {
        e?.preventDefault();
        setError(null);
        if (!codigoValido) {
            setError("Escribe un código como P01. Nunca el nombre de la persona.");
            return;
        }
        try {
            const datos = await obtenerEstado(codigo, sesion, soloG ? { opcionales: true, bloques: "G" } : {});
            setEstado(datos);
            setPracticar(!datos.tomas.some((t) => t.hecha));
        } catch (err) {
            setError(err.message);
        }
    }

    async function registrar(e) {
        e.preventDefault();
        setError(null);
        if (!registro.mano_dominante) return setError("Elige la mano dominante.");
        if (!registro.consentimiento) return setError("Sin el consentimiento firmado no se puede grabar.");
        try {
            await registrarPersona({ persona: codigo, ...registro });
            await consultar();
        } catch (err) {
            setError(err.message);
        }
    }

    function entregar() {
        const pendientes = estado.tomas.filter((t) => !t.hecha);
        onEmpezar({ persona: estado.persona, sesion: estado.sesion, pendientes,
                    total: estado.tomas.length, hechas: estado.tomas.length - pendientes.length }, practicar);
    }

    const sesiones = protocolo ? Object.keys(protocolo.sesiones) : ["1", "2"];
    const hechas = estado ? estado.tomas.filter((t) => t.hecha).length : 0;
    const opcion = (campo, valor, texto) => (
        <button type="button" className="g-btn g-opcion" aria-pressed={registro[campo] === valor}
            onClick={() => setRegistro((r) => ({ ...r, [campo]: valor }))}>{texto}</button>
    );

    return (
        <div className="g-app">
            <main className="g-marco g-marco--equipo">
                <p className="g-etiqueta">Pantalla del equipo</p>
                <h1 className="g-titulo">Grabación LSM-Connect</h1>
                <p className="g-nota">Esta pantalla la llena el equipo. Después, la persona sorda graba sola siguiendo las instrucciones.</p>

                <form className="g-form" onSubmit={consultar}>
                    <label className="g-campo">
                        <span>Código de la persona</span>
                        <input value={persona} onChange={(e) => { setPersona(e.target.value); setEstado(null); }}
                            placeholder="P01" maxLength={4} autoFocus aria-describedby="ayuda-codigo" />
                        <small id="ayuda-codigo">El código de la lista en papel. Nunca el nombre.</small>
                    </label>
                    <fieldset className="g-campo">
                        <legend>Sesión</legend>
                        <div className="g-fila">
                            {sesiones.map((s) => (
                                <button key={s} type="button" className="g-btn g-opcion" aria-pressed={sesion === s}
                                    onClick={() => { setSesion(s); setEstado(null); }}>Sesión {s}</button>
                            ))}
                        </div>
                    </fieldset>
                    <label className="g-check">
                        <input type="checkbox" checked={soloG} onChange={(e) => { setSoloG(e.target.checked); setEstado(null); }} />
                        <span>Grabar solo las <strong>frases del empleado</strong> (bloque G, para 1 o 2 personas)</span>
                    </label>
                    {!estado && <button className="g-btn g-btn--primario g-btn--grande" type="submit">Continuar</button>}
                </form>

                {error && <p className="g-mensaje" role="alert"><Pic.IcoAlerta /> {error}</p>}

                {estado && !estado.registrada && (
                    <form className="g-form" onSubmit={registrar}>
                        <h2 className="g-subtitulo">Registrar a {estado.persona} (solo la primera vez)</h2>
                        <fieldset className="g-campo"><legend>Mano dominante</legend>
                            <div className="g-fila">{opcion("mano_dominante", "derecha", "Derecha")}{opcion("mano_dominante", "izquierda", "Izquierda")}</div>
                        </fieldset>
                        <fieldset className="g-campo"><legend>Rango de edad</legend>
                            <div className="g-fila">{["<18", "18-25", "26-40", "41-60", ">60"].map((r) => <React.Fragment key={r}>{opcion("rango_edad", r, r)}</React.Fragment>)}</div>
                        </fieldset>
                        <fieldset className="g-campo"><legend>¿La LSM es su primera lengua?</legend>
                            <div className="g-fila">{opcion("lsm_lengua_materna", true, "Sí")}{opcion("lsm_lengua_materna", false, "No")}</div>
                        </fieldset>
                        <label className="g-campo"><span>Años usando LSM (aproximado)</span>
                            <input value={registro.anos_usando_lsm} onChange={(e) => setRegistro((r) => ({ ...r, anos_usando_lsm: e.target.value }))} />
                        </label>
                        <label className="g-campo"><span>Ciudad o región donde aprendió LSM</span>
                            <input value={registro.region} onChange={(e) => setRegistro((r) => ({ ...r, region: e.target.value }))} placeholder="Ensenada" />
                        </label>
                        <label className="g-campo"><span>Notas (opcional)</span>
                            <input value={registro.notas} onChange={(e) => setRegistro((r) => ({ ...r, notas: e.target.value }))} />
                        </label>
                        <label className="g-check g-check--importante">
                            <input type="checkbox" checked={registro.consentimiento}
                                onChange={(e) => setRegistro((r) => ({ ...r, consentimiento: e.target.checked }))} />
                            <span>La persona <strong>firmó el consentimiento informado</strong> y el intérprete se lo explicó en LSM.</span>
                        </label>
                        <button className="g-btn g-btn--primario g-btn--grande" type="submit">Registrar</button>
                    </form>
                )}

                {estado && estado.registrada && (
                    <section className="g-resumen">
                        <h2 className="g-subtitulo">{estado.persona} · Sesión {estado.sesion}</h2>
                        <p className="g-texto">
                            {hechas === estado.tomas.length ? "Esta sesión ya está completa."
                                : `Lleva ${hechas} de ${estado.tomas.length} tomas. Faltan unos ${minutos(estado.tomas.length - hechas)} minutos.`}
                        </p>
                        <p className="g-nota">Mano dominante: {estado.info.mano_dominante}</p>
                        <label className="g-check">
                            <input type="checkbox" checked={practicar} onChange={(e) => setPracticar(e.target.checked)} />
                            <span>Hacer 2 pruebas de práctica antes (recomendado la primera vez)</span>
                        </label>
                        <ol className="g-lista-equipo">
                            <li>Ajusta la cámara y la luz con la persona sentada enfrente.</li>
                            <li>Toca <strong>Entregar a la persona</strong> y deja que siga sola.</li>
                            <li>Si tiene dudas sobre una seña, el intérprete le explica; si no la conoce, puede saltarla.</li>
                        </ol>
                        <div className="g-fila">
                            <button className="g-btn g-btn--grande" onClick={() => setEstado(null)}>Cambiar</button>
                            <button className="g-btn g-btn--primario g-btn--grande" onClick={entregar} disabled={hechas === estado.tomas.length}>
                                Entregar a la persona <Pic.IcoSeguir />
                            </button>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}
