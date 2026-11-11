import React, { useState } from "react";
import { useCamara } from "./hooks/useCamara.js";
import { bonita, PALABRAS, TRAMITES_CLAVE } from "./palabras.js";

const RAPIDAS = ["Pase a caja", "Necesita su credencial", "Regrese mañana", "Llene este formato"];
const MAX_FICHAS = 5;   // fichas visibles en el panel del alumno
const MAX_TEXTO = 12;   // palabras visibles en el panel del empleado
const ERRORES = {
    permiso: "Necesitamos permiso para usar la cámara. Actívalo en el candado de la barra de direcciones.",
    camara: "No se encontró una cámara. Conéctala y pulsa Reintentar.",
    servidor: "No hay conexión con el servidor. Revisa que el backend esté encendido.",
};

export default function App() {
    const [modo, setModo] = useState("senas");   // "senas" (cámara) | "palabras" (el alumno toca las palabras)
    const [tramite, setTramite] = useState("Por definir");
    const [frase, setFrase] = useState([]);      // palabras reconocidas en esta atención
    const [ultimo, setUltimo] = useState(null);  // { palabra, confianza, top3 }
    const [duda, setDuda] = useState(null);      // top3 cuando el modelo no está seguro
    const [total, setTotal] = useState(0);
    const [respuesta, setRespuesta] = useState("");
    const [texto, setTexto] = useState("");
    const [escrito, setEscrito] = useState("");   // lo que el alumno escribe con el teclado
    const [vista, setVista] = useState(false);

    function agregar(palabra) {
        if (TRAMITES_CLAVE.includes(palabra)) setTramite(bonita(palabra));
        setFrase((f) => [...f, bonita(palabra)]);
        setTotal((n) => n + 1);
    }

    const { videoRef, estado, error, latenciaMs, reintentar } = useCamara({
        activa: modo === "senas",
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
        setFrase((f) => [...f, limpio]);
        setTotal((n) => n + 1);
        setUltimo({ palabra: limpio, confianza: 1, top3: [] });
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

    function responder(mensaje) {
        const limpio = mensaje.trim();
        if (!limpio) return;
        setRespuesta(limpio);
        setTexto("");
    }

    function nuevaAtencion() {
        setFrase([]); setTramite("Por definir"); setUltimo(null); setDuda(null); setTotal(0); setRespuesta(""); setTexto(""); setEscrito("");
    }

    const filas = duda ?? (ultimo?.top3?.length ? ultimo.top3 : ultimo?.palabra ? [{ palabra: ultimo.palabra, prob: ultimo.confianza }] : []);
    const pct = (p) => Math.round((p ?? 0) * 100);

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
                        <span className="ventanilla-tag">Servicios Escolares · Ventanilla 2</span>
                    </div>
                </div>
                <div className="topbar__franja-dorada"></div>
            </header>

            <main className="layout-grid">
                {/* PANEL 1: PALABRAS DISPONIBLES */}
                <section className="panel panel--tramites">
                    <h2 className="panel__titulo">Palabras disponibles</h2>
                    <p style={{ margin: "0 0 10px" }}>
                        {modo === "senas" ? "Estas son las señas que el sistema reconoce." : "Toca las palabras o escribe tu mensaje."}
                    </p>
                    <ul className="tramites">
                        {PALABRAS.map((p) => (
                            <li key={p}>
                                {modo === "palabras" ? (
                                    <button className="btn tramite" onClick={() => tocarPalabra(p)}>{bonita(p)}</button>
                                ) : (
                                    <span className="btn tramite" aria-pressed={ultimo?.palabra === p}>{bonita(p)}</span>
                                )}
                            </li>
                        ))}
                    </ul>
                </section>

                {/* PANEL 2: ALUMNO */}
                <section className="panel panel--alumno">
                    <span className="panel__etiqueta">Alumno</span>
                    <h2 className="panel__titulo">Traductor LSM</h2>

                    <div style={{ display: "flex", gap: 8, margin: "0 0 12px" }} role="group" aria-label="Forma de comunicarse">
                        <button className="btn tramite" style={{ flex: 1 }} aria-pressed={modo === "senas"} onClick={() => cambiarModo("senas")}>Con señas</button>
                        <button className="btn tramite" style={{ flex: 1 }} aria-pressed={modo === "palabras"} onClick={() => cambiarModo("palabras")}>Con palabras</button>
                    </div>

                    {modo === "senas" && (<>
                        <div className="camara">
                            <video
                                ref={videoRef}
                                muted
                                playsInline
                                aria-label="Vista de la cámara"
                                style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)" }}
                            />
                            {estado === "firmando" && <div className="buffer" style={{ zIndex: 1 }}></div>}
                            <span className="camara__aviso" style={{ position: "relative", zIndex: 1 }}>Procesado en memoria. Sin video guardado.</span>
                        </div>

                        {error ? (
                            <div role="alert" style={{ margin: "10px 0" }}>
                                <p>{ERRORES[error]}</p>
                                <button className="btn btn--chip" onClick={reintentar}>Reintentar</button>
                            </div>
                        ) : (
                            <p role="status" style={{ margin: "10px 0", fontWeight: 600 }}>
                                {estado === "firmando" ? "Reconociendo…" : "Listo: haz una seña y baja las manos al terminar"}
                            </p>
                        )}

                        <label className="switch">
                            <input type="checkbox" checked={vista} onChange={(e) => setVista(e.target.checked)} />
                            <span className="switch__pista">Vista del sistema</span>
                        </label>

                    </>)}

                    {modo === "palabras" && (
                        <form className="campo" style={{ margin: "0 0 10px" }} onSubmit={(e) => { e.preventDefault(); enviarEscrito(); }}>
                            <input type="text" value={escrito} onChange={(e) => setEscrito(e.target.value)} placeholder="Escribe tu mensaje aquí..." aria-label="Mensaje del alumno" maxLength={200} />
                            <button type="submit" className="btn btn--primario" disabled={!escrito.trim()}>Enviar</button>
                        </form>
                    )}

                    {modo === "palabras" && frase.length > 0 && (
                        <button className="btn btn--chip" onClick={borrarUltima} style={{ margin: "0 0 10px" }}>Borrar lo último</button>
                    )}

                    {duda && modo === "senas" && <p style={{ fontWeight: 700, margin: "10px 0 4px" }}>¿Qué quisiste decir? Toca una opción:</p>}
                    {modo === "senas" && (vista || duda) && filas.length > 0 && (
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
                                    <span>{bonita(c.palabra)}</span>
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

                    {respuesta && <div className="respuesta-alumno">{respuesta}</div>}
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
                    </p>

                    <div className="rapidas">
                        {RAPIDAS.map((r) => (
                            <button key={r} className="btn btn--chip" onClick={() => responder(r)}>{r}</button>
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
                                <span className="metrica__nombre">Señas reconocidas</span>
                            </div>
                        </div>
                    )}

                    <button className="btn btn--chip" onClick={nuevaAtencion} style={{ marginTop: 12 }}>Nueva atención</button>
                </section>
            </main>

            <footer className="pie">
                <div className="pie__enlaces">
                    <a href="#" className="pie__enlace">Correo</a>
                    <a href="#" className="pie__enlace">Biblioteca</a>
                    <a href="#" className="pie__enlace">Gaceta</a>
                    <a href="#" className="pie__enlace">Radio</a>
                    <a href="#" className="pie__enlace">Política de Privacidad</a>
                </div>
                <div className="pie__banda">
                    <img src="/logo-uabc.png" alt="" className="pie__escudo-mini" />
                </div>
            </footer>
        </div>
    );
}
