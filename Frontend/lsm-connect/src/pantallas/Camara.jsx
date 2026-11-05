import { useState } from "react";
import { useCamara } from "../hooks/useCamara.js";
import ListaMensajes from "../componentes/ListaMensajes.jsx";

const MENSAJES_ERROR = {
  permiso: "Necesitamos permiso para usar la cámara. Actívalo en el navegador y pulsa Reintentar.",
  camara: "No se encontró una cámara. Conéctala y pulsa Reintentar.",
  servidor: "No hay conexión con el servidor. Revisa que esté encendido y pulsa Reintentar.",
};

export default function Camara({ chat, onVolver, onTerminar }) {
  const [ultima, setUltima] = useState(null); // última palabra reconocida
  const [duda, setDuda] = useState(null);     // { top3: [...] } cuando el modelo no está seguro

  const { videoRef, estado, error, reintentar } = useCamara({
    activa: true,
    onPalabra: (r) => {
      setDuda(null);
      setUltima(r.palabra);
      chat.enviar(r.palabra); // llega a la ventanilla como mensaje del estudiante
    },
    onDuda: (r) => setDuda({ top3: r.top3 }),
  });

  function elegir(palabra) {
    chat.enviar(palabra);
    setUltima(palabra);
    setDuda(null);
  }

  return (
    <main className="pantalla">
      <header className="barra">
        <h1>Cámara</h1>
        <div className="acciones">
          <button className="boton" onClick={onVolver}>Pasar a chat</button>
          <button className="boton peligro" onClick={onTerminar}>Terminar atención</button>
        </div>
      </header>

      {error && (
        <div className="aviso" role="alert">
          <p>{MENSAJES_ERROR[error]}</p>
          <button className="boton" onClick={reintentar}>Reintentar</button>
        </div>
      )}

      <div className="camara-zona">
        <video ref={videoRef} className="video-espejo" muted playsInline aria-label="Vista de la cámara" />
        <p className={`estado ${estado}`} aria-live="polite">
          {estado === "firmando" ? "Reconociendo…" : "Listo: haz una seña"}
        </p>
      </div>

      {duda ? (
        <section className="duda" aria-label="¿Qué quisiste decir?">
          <h2>¿Qué quisiste decir?</h2>
          <div className="opciones">
            {duda.top3.map((c) => (
              <button key={c.palabra} className="boton grande" onClick={() => elegir(c.palabra)}>
                {c.palabra}
              </button>
            ))}
            <button className="boton" onClick={() => setDuda(null)}>Ninguna de estas</button>
          </div>
        </section>
      ) : (
        <p className="palabra-grande" aria-live="polite">{ultima ?? " "}</p>
      )}

      <ListaMensajes mensajes={chat.mensajes} miRol="estudiante" compacta />
    </main>
  );
}
