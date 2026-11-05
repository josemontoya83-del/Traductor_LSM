import { useCallback, useEffect, useRef, useState } from "react";
import { WS, API, SALA } from "../config.js";

/**
 * Conexión al chat del backend. Se reconecta sola si se cae.
 * estado: "conectando" | "conectado" | "caido"
 */
export function useChat(rol) {
  const [mensajes, setMensajes] = useState([]);
  const [estado, setEstado] = useState("conectando");
  const [cerrada, setCerrada] = useState(0); // sube en 1 cada vez que se cierra la atención
  const wsRef = useRef(null);

  useEffect(() => {
    let vivo = true;
    let temporizador;

    function conectar() {
      setEstado("conectando");
      const ws = new WebSocket(`${WS}/ws/chat?rol=${rol}&sala=${SALA}`);
      wsRef.current = ws;
      ws.onopen = () => vivo && setEstado("conectado");
      ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.tipo === "historial") setMensajes(d.mensajes);
        else if (d.tipo === "mensaje") setMensajes((m) => [...m, d]);
        else if (d.tipo === "cerrada") {
          setMensajes([]);
          setCerrada((n) => n + 1);
        }
      };
      ws.onclose = () => {
        if (!vivo) return;
        setEstado("caido");
        temporizador = setTimeout(conectar, 2000); // reintenta cada 2 s
      };
    }

    conectar();
    return () => {
      vivo = false;
      clearTimeout(temporizador);
      wsRef.current?.close();
    };
  }, [rol]);

  const enviar = useCallback((texto) => {
    const limpio = texto.trim();
    if (!limpio || wsRef.current?.readyState !== WebSocket.OPEN) return false;
    wsRef.current.send(JSON.stringify({ texto: limpio }));
    return true;
  }, []);

  const cerrarAtencion = useCallback(async () => {
    try {
      await fetch(`${API}/chat/${SALA}/cerrar`, { method: "POST" });
    } catch {
      setMensajes([]); // si el backend no responde, al menos se limpia esta pantalla
    }
  }, []);

  return { mensajes, estado, enviar, cerrarAtencion, cerrada };
}
