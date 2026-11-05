import { useEffect, useRef, useState } from "react";
import ListaMensajes from "../componentes/ListaMensajes.jsx";

/** Pantalla de chat. La usan el estudiante y la ventanilla (cambia solo `rol`). */
export default function Chat({ rol, chat, onVolver, onTerminar }) {
  const [texto, setTexto] = useState("");
  const { mensajes, estado, enviar } = chat;

  function mandar(e) {
    e.preventDefault();
    if (enviar(texto)) setTexto("");
  }

  return (
    <main className="pantalla">
      <header className="barra">
        <h1>{rol === "ventanilla" ? "Ventanilla" : "Chat"}</h1>
        <div className="acciones">
          {onVolver && <button className="boton" onClick={onVolver}>Cambiar modo</button>}
          {onTerminar && <button className="boton peligro" onClick={onTerminar}>Terminar atención</button>}
        </div>
      </header>
      {estado !== "conectado" && (
        <p className="aviso" role="alert">
          {estado === "conectando" ? "Conectando…" : "Sin conexión con el servidor. Reintentando…"}
        </p>
      )}
      <ListaMensajes mensajes={mensajes} miRol={rol} />
      <form className="formulario" onSubmit={mandar}>
        <input
          className="campo"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribe tu mensaje…"
          aria-label="Mensaje"
          maxLength={500}
          autoFocus
        />
        <button className="boton principal" type="submit" disabled={!texto.trim() || estado !== "conectado"}>
          Enviar
        </button>
      </form>
    </main>
  );
}
