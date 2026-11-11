import { useEffect, useRef, useState } from "react";
import { WS, FRAME_ANCHO, FRAME_ALTO, FRAME_CALIDAD } from "../config.js";

/**
 * Abre la cámara y manda frames JPEG a /ws/camara.
 * Manda el siguiente frame SOLO cuando llega la respuesta del anterior.
 * Los frames se mandan SIN espejo (el espejo es solo visual, en el CSS del video).
 *
 * error: null | "permiso" | "camara" | "servidor"
 */
export function useCamara({ activa, onPalabra, onDuda }) {
  const videoRef = useRef(null);
  const [estado, setEstado] = useState("reposo"); // reposo | firmando
  const [error, setError] = useState(null);
  const [reintentos, setReintentos] = useState(0);
  const [latenciaMs, setLatenciaMs] = useState(null);
  const t0 = useRef(0);
  const ultimoId = useRef(0);
  // Para que los callbacks siempre sean los más recientes sin reiniciar la cámara
  const cbPalabra = useRef(onPalabra);
  const cbDuda = useRef(onDuda);
  cbPalabra.current = onPalabra;
  cbDuda.current = onDuda;

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
      ws.onopen = enviarFrame;
      ws.onerror = () => vivo && setError("servidor");
      ws.onclose = () => vivo && setError((e) => e ?? "servidor");
      ws.onmessage = (e) => {
        const r = JSON.parse(e.data);
        if (t0.current) setLatenciaMs(Math.round(performance.now() - t0.current));
        setEstado(r.estado === "firmando" ? "firmando" : "reposo");
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
      ws?.close();
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [activa, reintentos]);

  return { videoRef, estado, error, latenciaMs, reintentar: () => setReintentos((n) => n + 1) };
}
