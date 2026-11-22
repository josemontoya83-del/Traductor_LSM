import { useEffect, useRef, useState } from "react";
import { WS, FRAME_ANCHO, FRAME_ALTO, FRAME_CALIDAD } from "../config.js";

/**
 * Abre la cámara y manda frames JPEG a /ws/camara.
 * Manda el siguiente frame SOLO cuando llega la respuesta del anterior.
 * Los frames se mandan SIN espejo (el espejo es solo visual, en el CSS del video).
 * El modo (senas | deletreo | numeros) y los dominios se mandan por el mismo WebSocket:
 * cambiarlos NO reconecta la cámara.
 *
 * error: null | "permiso" | "camara" | "servidor"
 */
export function useCamara({ activa, modo, dominios, onPalabra, onDuda }) {
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const [estado, setEstado] = useState("reposo"); // reposo | firmando | letra
  const [parcial, setParcial] = useState("");     // deletreo en curso
  const [aviso, setAviso] = useState(null);       // mensaje del servidor (p. ej. falta un modelo)
  const [error, setError] = useState(null);
  const [reintentos, setReintentos] = useState(0);
  const [latenciaMs, setLatenciaMs] = useState(null);
  const t0 = useRef(0);
  const ultimoId = useRef(0);
  const cbPalabra = useRef(onPalabra);
  const cbDuda = useRef(onDuda);
  const config = useRef({ modo, dominios });
  cbPalabra.current = onPalabra;
  cbDuda.current = onDuda;
  config.current = { modo, dominios };

  function mandarConfig() {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ tipo: "config", ...config.current }));
    }
  }

  useEffect(() => {
    mandarConfig();
    setParcial("");
  }, [modo, dominios.join(",")]);

  useEffect(() => {
    if (!activa) return;
    let vivo = true;
    let stream;
    let ws;
    const canvas = document.createElement("canvas");
    canvas.width = FRAME_ANCHO;
    canvas.height = FRAME_ALTO;
    setError(null);
    ultimoId.current = 0;

    function enviarFrame() {
      const video = videoRef.current;
      if (!vivo || !ws || ws.readyState !== WebSocket.OPEN) return;
      if (!video || video.videoWidth === 0) {
        setTimeout(enviarFrame, 100); // la cámara todavía no tiene imagen
        return;
      }
      canvas.getContext("2d").drawImage(video, 0, 0, FRAME_ANCHO, FRAME_ALTO);
      canvas.toBlob(
        (blob) => blob && blob.arrayBuffer().then((buf) => {
          if (!vivo || ws.readyState !== WebSocket.OPEN) return;
          t0.current = performance.now();
          ws.send(buf);
        }),
        "image/jpeg",
        FRAME_CALIDAD
      );
    }

    async function iniciar() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: FRAME_ANCHO, height: FRAME_ALTO },
          audio: false,
        });
      } catch (e) {
        setError(e.name === "NotAllowedError" ? "permiso" : "camara");
        return;
      }
      if (!vivo) return stream.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = stream;
      await videoRef.current.play().catch(() => {});

      ws = new WebSocket(`${WS}/ws/camara`);
      wsRef.current = ws;
      ws.onopen = () => {
        mandarConfig();
        enviarFrame();
      };
      ws.onerror = () => vivo && setError("servidor");
      ws.onclose = () => vivo && setError((e) => e ?? "servidor");
      ws.onmessage = (e) => {
        const r = JSON.parse(e.data);
        if (t0.current) setLatenciaMs(Math.round(performance.now() - t0.current));
        setEstado(r.estado === "firmando" || r.estado === "letra" ? r.estado : "reposo");
        setParcial(r.parcial ?? "");
        setAviso(r.aviso ?? null);
        if ((r.estado === "palabra" || r.estado === "duda") && r.id > ultimoId.current) {
          ultimoId.current = r.id; // cada evento se procesa una sola vez
          if (r.estado === "palabra") cbPalabra.current?.(r);
          else cbDuda.current?.(r);
        }
        enviarFrame();
      };
    }

    iniciar();
    return () => {
      vivo = false;
      wsRef.current = null;
      ws?.close();
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [activa, reintentos]);

  return { videoRef, estado, parcial, aviso, error, latenciaMs, reintentar: () => setReintentos((n) => n + 1) };
}
