import { useCallback, useEffect, useRef, useState } from "react";
import { WS } from "../config.js";

const ANCHO_REVISION = 640;   // imágenes chicas para /ws/revision (el video se graba completo)
const TIPOS_VIDEO = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"];

/**
 * Cámara para la grabación en el navegador:
 *  - graba el video completo con MediaRecorder (iniciar / detener / cancelar);
 *  - en paralelo manda imágenes chicas a /ws/revision y expone `revision`
 *    ({ encuadre, hombros, mano, activa }) para que la toma empiece y termine sola.
 * error: null | "permiso" | "camara" | "servidor" | "grabadora"
 */
export function useCamaraGrabacion(activa) {
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const wsRef = useRef(null);
    const grabadoraRef = useRef(null);
    const revRef = useRef({ encuadre: "sin_persona", hombros: false, mano: false, activa: false, t: 0 });
    const [revision, setRevision] = useState(revRef.current);
    const [error, setError] = useState(null);
    const [ajustes, setAjustes] = useState(null);
    const [reintentos, setReintentos] = useState(0);

    useEffect(() => {
        if (!activa) return;
        let vivo = true;
        let ws;
        const canvas = document.createElement("canvas");
        setError(null);

        function enviar() {
            const v = videoRef.current;
            if (!vivo || !ws || ws.readyState !== WebSocket.OPEN) return;
            if (!v || v.videoWidth === 0) {
                setTimeout(enviar, 100);
                return;
            }
            canvas.width = ANCHO_REVISION;
            canvas.height = Math.round((ANCHO_REVISION * v.videoHeight) / v.videoWidth);
            canvas.getContext("2d").drawImage(v, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((b) => b && b.arrayBuffer().then((buf) => {
                if (vivo && ws.readyState === WebSocket.OPEN) ws.send(buf);
            }), "image/jpeg", 0.6);
        }

        async function iniciar() {
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
                    audio: false,
                });
            } catch (e) {
                if (vivo) setError(e.name === "NotAllowedError" ? "permiso" : "camara");
                return;
            }
            if (!vivo) return stream.getTracks().forEach((t) => t.stop());
            streamRef.current = stream;
            const s = stream.getVideoTracks()[0].getSettings();
            setAjustes({ ancho: s.width, alto: s.height, fps: s.frameRate });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play().catch(() => {});
            }
            ws = new WebSocket(`${WS}/ws/revision`);
            wsRef.current = ws;
            ws.onopen = enviar;
            ws.onerror = () => vivo && setError("servidor");
            ws.onclose = () => vivo && setError((e) => e ?? "servidor");
            ws.onmessage = (e) => {
                const r = { ...JSON.parse(e.data), t: performance.now() };
                revRef.current = r;
                setRevision(r);
                enviar();
            };
        }

        iniciar();
        return () => {
            vivo = false;
            wsRef.current = null;
            ws?.close();
            grabadoraRef.current?.recorder?.state === "recording" && grabadoraRef.current.recorder.stop();
            streamRef.current?.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
        };
    }, [activa, reintentos]);

    // Si el <video> se monta después de abrir la cámara (cambio de pantalla), se le conecta el stream.
    const conectarVideo = useCallback((el) => {
        videoRef.current = el;
        if (el && streamRef.current && el.srcObject !== streamRef.current) {
            el.srcObject = streamRef.current;
            el.play().catch(() => {});
        }
    }, []);

    const fase = useCallback((f) => {
        const ws = wsRef.current;
        if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ tipo: "fase", fase: f }));
    }, []);

    const iniciarGrabacion = useCallback(() => {
        const stream = streamRef.current;
        if (!stream || typeof MediaRecorder === "undefined") {
            setError("grabadora");
            return false;
        }
        const mimeType = TIPOS_VIDEO.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
        const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 4_000_000 });
        const partes = [];
        recorder.ondataavailable = (e) => e.data.size && partes.push(e.data);
        recorder.start(250);
        grabadoraRef.current = { recorder, partes, t0: performance.now() };
        return true;
    }, []);

    const detenerGrabacion = useCallback(() => new Promise((resolver) => {
        const g = grabadoraRef.current;
        grabadoraRef.current = null;
        if (!g) return resolver(null);
        g.recorder.onstop = () => resolver({
            blob: new Blob(g.partes, { type: g.recorder.mimeType || "video/webm" }),
            duracion: (performance.now() - g.t0) / 1000,
        });
        g.recorder.stop();
    }), []);

    const cancelarGrabacion = useCallback(() => {
        const g = grabadoraRef.current;
        grabadoraRef.current = null;
        if (g && g.recorder.state === "recording") {
            g.recorder.onstop = null;
            g.recorder.stop();
        }
    }, []);

    return {
        conectarVideo, revision, revRef, error, ajustes, fase,
        iniciarGrabacion, detenerGrabacion, cancelarGrabacion,
        reintentar: () => setReintentos((n) => n + 1),
    };
}
