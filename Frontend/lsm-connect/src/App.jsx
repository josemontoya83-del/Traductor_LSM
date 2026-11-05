import { useEffect, useState } from "react";
import Inicio from "./pantallas/Inicio.jsx";
import Chat from "./pantallas/Chat.jsx";
import Camara from "./pantallas/Camara.jsx";
import { useChat } from "./hooks/useChat.js";
import { ROL_URL } from "./config.js";

export default function App() {
  const [pantalla, setPantalla] = useState(ROL_URL === "ventanilla" ? "chat" : "inicio");
  // El chat vive aquí arriba para que la conversación no se pierda al cambiar de pantalla
  const chat = useChat(ROL_URL);

  // Cuando alguien cierra la atención, esta pantalla vuelve al inicio (la ventanilla se queda en su chat)
  useEffect(() => {
    if (chat.cerrada > 0 && ROL_URL !== "ventanilla") setPantalla("inicio");
  }, [chat.cerrada]);

  async function terminar() {
    await chat.cerrarAtencion();
    setPantalla("inicio");
  }

  if (ROL_URL === "ventanilla") {
    return <Chat rol="ventanilla" chat={chat} onTerminar={terminar} />;
  }
  if (pantalla === "camara") {
    return <Camara chat={chat} onVolver={() => setPantalla("chat")} onTerminar={terminar} />;
  }
  if (pantalla === "chat") {
    return <Chat rol="estudiante" chat={chat} onVolver={() => setPantalla("inicio")} onTerminar={terminar} />;
  }
  return <Inicio onElegir={setPantalla} />;
}
