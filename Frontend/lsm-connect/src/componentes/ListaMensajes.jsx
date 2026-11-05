import { useEffect, useRef } from "react";

export default function ListaMensajes({ mensajes, miRol, compacta = false }) {
  const fin = useRef(null);
  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes]);

  const visibles = compacta ? mensajes.slice(-3) : mensajes;
  return (
    <div className={compacta ? "mensajes compacta" : "mensajes"} aria-live="polite" role="log">
      {visibles.length === 0 && <p className="vacio">Todavía no hay mensajes.</p>}
      {visibles.map((m, i) => (
        <div key={i} className={`burbuja ${m.rol === miRol ? "mia" : "otra"}`}>
          <span className="quien">{m.rol === "estudiante" ? "Estudiante" : "Ventanilla"}</span>
          <span className="texto">{m.texto}</span>
        </div>
      ))}
      <div ref={fin} />
    </div>
  );
}
