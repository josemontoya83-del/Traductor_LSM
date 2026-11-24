import { useCallback, useEffect, useRef, useState } from "react";
import { WS, API, SALA } from "../config.js";

/**
 * Conexión al chat del backend (/ws/chat). Se reconecta sola si se cae.
 * Con esto se comunican la pantalla del alumno y la del empleado: lo que reconoce la cámara
 * se manda como mensaje del "estudiante" y las respuestas como mensajes de "ventanilla".
 *
 * activo: false = no se conecta (por ejemplo, la pantalla del empleado no manda como alumno).
 * estado: "apagado" | "conectando" | "conectado" | "caido"
 */
export function useChat(rol, activo = true) {
  const [mensajes, setMensajes] = useState([]);
  const [estado, setEstado] = useState(activo ? "conectando" : "apagado");
  const [cerrada, setCerrada] = useState(0); // sube en 1 cada vez que se cierra la atención
  const wsRef = useRef(null);

  useEffect(() => {
    if (!activo) {
      setEstado("apagado");
      return;
    }
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
  }, [rol, activo]);

  const mandar = useCallback((datos) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
    wsRef.current.send(JSON.stringify(datos));
    return true;
  }, []);

  const enviar = useCallback((texto) => {
    const limpio = texto.trim();
    return limpio ? mandar({ texto: limpio }) : false;
  }, [mandar]);

  const borrarUltimo = useCallback(() => mandar({ borrar: true }), [mandar]);

  const cerrarAtencion = useCallback(async () => {
    try {
      await fetch(`${API}/chat/${SALA}/cerrar`, { method: "POST" });
    } catch {
      setMensajes([]); // si el backend no responde, al menos se limpia esta pantalla
    }
  }, []);

  return { mensajes, estado, enviar, borrarUltimo, cerrarAtencion, cerrada };
}
