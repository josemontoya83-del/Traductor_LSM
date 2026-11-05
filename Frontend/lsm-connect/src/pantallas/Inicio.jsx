export default function Inicio({ onElegir }) {
  return (
    <main className="pantalla centrada">
      <h1>LSM-Connect</h1>
      <p className="lead">¿Cómo quieres comunicarte?</p>
      <div className="botones-grandes">
        <button className="boton grande" onClick={() => onElegir("camara")}>
          <span className="icono" aria-hidden="true">🤟</span>
          Cámara (señas)
        </button>
        <button className="boton grande" onClick={() => onElegir("chat")}>
          <span className="icono" aria-hidden="true">💬</span>
          Chat (texto)
        </button>
      </div>
    </main>
  );
}
