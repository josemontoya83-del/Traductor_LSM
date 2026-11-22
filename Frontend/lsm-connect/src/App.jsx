import React, { useEffect, useMemo, useState } from "react";
import { API, DOMINIOS, VENTANILLA } from "./config.js";
import { useCamara } from "./hooks/useCamara.js";

const MAX_FICHAS = 5;   // fichas visibles en el panel del alumno
const MAX_TEXTO = 12;   // palabras visibles en el panel del empleado
const MODOS = [
    { id: "senas", nombre: "Señas", ayuda: "Haz una seña y baja las manos al terminar." },
    { id: "deletreo", nombre: "Deletreo", ayuda: "Deletrea letra por letra (nombres, carreras...). Baja la mano al terminar la palabra." },
    { id: "numeros", nombre: "Números", ayuda: "Deletrea los dígitos (matrícula, teléfono). Baja la mano al terminar." },
    { id: "teclado", nombre: "Teclado", ayuda: "Toca las palabras o escribe tu mensaje." },
];
const ERRORES = {
    permiso: "Necesitamos permiso para usar la cámara. Actívalo en el candado de la barra de direcciones.",
    camara: "No se encontró una cámara. Conéctala y pulsa Reintentar.",
    servidor: "No hay conexión con el servidor. Revisa que el backend esté encendido.",
};

export default function App() {
    const [modo, setModo] = useState("senas");
    const [vocab, setVocab] = useState({ senas: [], respuestas: [], dominios_disponibles: [], dominios_activos: [] });
    const [tramite, setTramite] = useState("Por definir");
    const [frase, setFrase] = useState([]);      // palabras reconocidas en esta atención
    const [ultimo, setUltimo] = useState(null);  // { palabra, confianza, top3 }
    const [duda, setDuda] = useState(null);      // top3 cuando el sistema no está seguro
    const [total, setTotal] = useState(0);
    const [respuesta, setRespuesta] = useState(null); // { texto, id? }
    const [texto, setTexto] = useState("");
    const [escrito, setEscrito] = useState("");
    const [vista, setVista] = useState(false);
    const [sinVideo, setSinVideo] = useState(false);

    // Vocabulario de esta ventanilla: general + dominios de la URL (?dominio=escolar)
    useEffect(() => {
        fetch(`${API}/vocabulario?dominios=${DOMINIOS.join(",")}`)
            .then((r) => r.json())
            .then(setVocab)
            .catch(() => {});
    }, []);

    const tramites = useMemo(() => new Set(vocab.senas.filter((s) => s.tramite).map((s) => s.texto)), [vocab]);
    const nombreDominio = vocab.dominios_disponibles
        .filter((d) => d.id !== "general" && vocab.dominios_activos.includes(d.id))
        .map((d) => d.nombre).join(" · ") || "Ventanilla";

    function agregar(palabra) {
        if (tramites.has(palabra)) setTramite(palabra);
        setFrase((f) => [...f, palabra]);
        setTotal((n) => n + 1);
    }

    const camaraActiva = modo !== "teclado";
    const { videoRef, estado, parcial, aviso, error, latenciaMs, reintentar } = useCamara({
        activa: camaraActiva,
        modo: camaraActiva ? modo : "senas",
        dominios: DOMINIOS,
        onPalabra: (r) => {
            setDuda(null);
            agregar(r.palabra);
            setUltimo({ palabra: r.palabra, confianza: r.confianza, top3: r.top3 ?? [] });
        },
        onDuda: (r) => {
            setDuda(r.top3);
            setUltimo({ palabra: r.top3?.[0]?.palabra, confianza: r.top3?.[0]?.prob ?? 0, top3: r.top3 });
        },
    });

    function tocarPalabra(palabra) {
        agregar(palabra);
        setUltimo({ palabra, confianza: 1, top3: [] });
    }

    function enviarEscrito() {
        const limpio = escrito.trim();
        if (!limpio) return;
        tocarPalabra(limpio);
        setEscrito("");
    }

    function borrarUltima() {
        setFrase((f) => f.slice(0, -1));
        setTotal((n) => Math.max(0, n - 1));
    }

    function cambiarModo(m) {
        setModo(m);
        setDuda(null);
    }

    function elegirDuda(palabra) {
        agregar(palabra);
        setDuda(null);
    }

    function responder(mensaje, id = null) {
        const limpio = mensaje.trim();
        if (!limpio) return;
        setRespuesta({ texto: limpio, id });
        setSinVideo(false);
        setTexto("");
    }

    function nuevaAtencion() {
        setFrase([]); setTramite("Por definir"); setUltimo(null); setDuda(null); setTotal(0);
        setRespuesta(null); setTexto(""); setEscrito("");
    }

    const filas = duda ?? (ultimo?.top3?.length ? ultimo.top3 : ultimo?.palabra ? [{ palabra: ultimo.palabra, prob: ultimo.confianza }] : []);
    const pct = (p) => Math.round((p ?? 0) * 100);
    const ayuda = MODOS.find((m) => m.id === modo)?.ayuda;
    const deletreando = modo === "deletreo" || modo === "numeros";

    return (
        <div className="app-container">
            {/* ENCABEZADO */}
            <header className="topbar-wrapper">
                <div className="topbar">
                    <div className="brand">
                        <img src="/logo-uabc.png" alt="Escudo UABC" className="brand__escudo" />
                        <div className="brand__divisor"></div>
                        <h1 className="brand__nombre">
                            UABC <span className="brand__sub">LSM-Connect</span>
                        </h1>
                    </div>
                    <div className="topbar__info">
                        <span className="ventanilla-tag">{nombreDominio} · Ventanilla {VENTANILLA}</span>
                    </div>
                </div>
                <div className="topbar__franja-dorada"></div>
            </header>

            <main className="layout-grid">
                {/* PANEL 1: VOCABULARIO */}
                <section className="panel panel--tramites">
                    <h2 className="panel__titulo">{deletreando ? "Deletreo" : "Señas disponibles"}</h2>
                    {deletreando ? (
                        <p style={{ margin: "0 0 10px" }}>
                            Con el deletreo puedes escribir <strong>cualquier palabra</strong>: nombres, carreras,
                            calles... Si se parece a una palabra conocida, el sistema te la sugiere.
                        </p>
                    ) : (
                        <>
                            <p style={{ margin: "0 0 10px" }}>
                                {modo === "senas" ? "Estas son las señas que el sistema reconoce." : "Toca las palabras o escribe tu mensaje."}
                            </p>
                            <ul className="tramites">
                                {vocab.senas.map((s) => (
                                    <li key={s.id}>
                                        {modo === "teclado" ? (
                                            <button className="btn tramite" onClick={() => tocarPalabra(s.texto)}>{s.texto}</button>
                                        ) : (
                                            <span className="btn tramite" aria-pressed={ultimo?.palabra === s.texto}>{s.texto}</span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </>
                    )}
                </section>

                {/* PANEL 2: ALUMNO */}
                <section className="panel panel--alumno">
                    <span className="panel__etiqueta">Alumno</span>
                    <h2 className="panel__titulo">Traductor LSM</h2>

                    <div className="modos" role="group" aria-label="Forma de comunicarse">
                        {MODOS.map((m) => (
                            <button key={m.id} className="btn tramite" aria-pressed={modo === m.id} onClick={() => cambiarModo(m.id)}>
                                {m.nombre}
                            </button>
                        ))}
                    </div>

                    {camaraActiva && (<>
                        <div className="camara">
                            <video
                                ref={videoRef}
                                muted
                                playsInline
                                aria-label="Vista de la cámara"
                                style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)" }}
                            />
                            {estado !== "reposo" && <div className="buffer" style={{ zIndex: 1 }}></div>}
                            <span className="camara__aviso" style={{ position: "relative", zIndex: 1 }}>Procesado en memoria. Sin video guardado.</span>
                        </div>

                        {deletreando && (
                            <div className="parcial" aria-live="polite">{parcial || " "}</div>
                        )}

                        <details className="guia">
                            <summary>Cómo usarlo</summary>
                            <ol>
                                <li>Colócate de modo que se vean <strong>tu cabeza, hombros y pecho</strong>.</li>
                                <li>Puedes usar la mano derecha o la izquierda.</li>
                                <li>Empieza con las manos abajo y, al terminar, <strong>baja las manos</strong> y espera un segundo.</li>
                            </ol>
                        </details>

                        {error ? (
                            <div role="alert" style={{ margin: "10px 0" }}>
                                <p>{ERRORES[error]}</p>
                                <button className="btn btn--chip" onClick={reintentar}>Reintentar</button>
                            </div>
                        ) : aviso ? (
                            <p role="alert" className="aviso">{aviso}</p>
                        ) : (
                            <p role="status" style={{ margin: "10px 0", fontWeight: 600 }}>
                                {estado === "reposo" ? ayuda : deletreando ? "Leyendo letras…" : "Reconociendo…"}
                            </p>
                        )}

                        <label className="switch">
                            <input type="checkbox" checked={vista} onChange={(e) => setVista(e.target.checked)} />
                            <span className="switch__pista">Vista del sistema</span>
                        </label>
                    </>)}

                    {modo === "teclado" && (
                        <form className="campo" style={{ margin: "0 0 10px" }} onSubmit={(e) => { e.preventDefault(); enviarEscrito(); }}>
                            <input type="text" value={escrito} onChange={(e) => setEscrito(e.target.value)} placeholder="Escribe tu mensaje aquí..." aria-label="Mensaje del alumno" maxLength={200} />
                            <button type="submit" className="btn btn--primario" disabled={!escrito.trim()}>Enviar</button>
                        </form>
                    )}

                    {frase.length > 0 && (
                        <button className="btn btn--chip" onClick={borrarUltima} style={{ margin: "0 0 10px" }}>Borrar lo último</button>
                    )}

                    {duda && camaraActiva && <p style={{ fontWeight: 700, margin: "10px 0 4px" }}>¿Qué quisiste decir? Toca una opción:</p>}
                    {camaraActiva && (vista || duda) && filas.length > 0 && (
                        <div className="top3">
                            {filas.map((c) => (
                                <div
                                    key={c.palabra}
                                    className="pred"
                                    {...(duda ? {
                                        role: "button", tabIndex: 0, style: { cursor: "pointer" },
                                        onClick: () => elegirDuda(c.palabra),
                                        onKeyDown: (e) => (e.key === "Enter" || e.key === " ") && elegirDuda(c.palabra)
                                    } : {})}
                                >
                                    <span>{c.palabra}</span>
                                    <div className="pred__barra"><span style={{ width: `${pct(c.prob)}%` }}></span></div>
                                    <span className="pred__pct">{pct(c.prob)}%</span>
                                </div>
                            ))}
                            {duda && <button className="btn btn--chip" onClick={() => setDuda(null)}>Ninguna de estas</button>}
                        </div>
                    )}

                    <div className="frase">
                        {frase.length === 0 && <span className="ficha">Aquí aparecen tus señas</span>}
                        {frase.slice(-MAX_FICHAS).map((p, i, visibles) => (
                            <span key={frase.length - visibles.length + i} className={i === visibles.length - 1 ? "ficha ficha--ultima" : "ficha"}>{p}</span>
                        ))}
                    </div>

                    {respuesta && (
                        <div className="respuesta-alumno">
                            {respuesta.id && !sinVideo && (
                                <video
                                    key={respuesta.id}
                                    className="respuesta-video"
                                    src={`/respuestas/${respuesta.id}.mp4`}
                                    autoPlay
                                    loop
                                    muted
                                    playsInline
                                    onError={() => setSinVideo(true)}
                                    aria-label={`Respuesta en LSM: ${respuesta.texto}`}
                                />
                            )}
                            <span>{respuesta.texto}</span>
                        </div>
                    )}
                </section>

                {/* PANEL 3: EMPLEADO */}
                <section className="panel panel--empleado">
                    <span className="panel__etiqueta">Empleado</span>
                    <h2 className="panel__titulo">Panel de atención</h2>
                    <span className="panel__etiqueta">Trámite: {tramite}</span>

                    <p className="traduccion" aria-live="polite">
                        {frase.length
                            ? (frase.length > MAX_TEXTO ? "… " : "") + frase.slice(-MAX_TEXTO).join(" ")
                            : "Esperando las señas del alumno…"}
                        {deletreando && parcial && <span className="traduccion__parcial"> {parcial}…</span>}
                    </p>

                    <div className="rapidas">
                        {vocab.respuestas.map((r) => (
                            <button key={r.id} className="btn btn--chip" onClick={() => responder(r.texto, r.id)}>{r.texto}</button>
                        ))}
                    </div>

                    <form className="campo" onSubmit={(e) => { e.preventDefault(); responder(texto); }}>
                        <input type="text" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe tu respuesta aquí..." aria-label="Respuesta" maxLength={300} />
                        <button type="submit" className="btn btn--primario" disabled={!texto.trim()}>Enviar</button>
                    </form>

                    {vista && (
                        <div className="metricas">
                            <div className="metrica">
                                <span className="metrica__valor">{latenciaMs ?? "–"}{latenciaMs != null && " ms"}</span>
                                <span className="metrica__nombre">Latencia</span>
                            </div>
                            <div className="metrica">
                                <span className="metrica__valor">{ultimo ? `${pct(ultimo.confianza)}%` : "–"}</span>
                                <span className="metrica__nombre">Confianza</span>
                            </div>
                            <div className="metrica">
                                <span className="metrica__valor">{total}</span>
                                <span className="metrica__nombre">Palabras</span>
                            </div>
                        </div>
                    )}

                    <button className="btn btn--chip" onClick={nuevaAtencion} style={{ marginTop: 12 }}>Nueva atención</button>
                </section>
            </main>

            <footer className="pie">
                <div className="pie__banda">
                    <img src="/logo-uabc.png" alt="" className="pie__escudo-mini" />
                </div>
            </footer>
        </div>
    );
}
