import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import Grabacion from "./grabacion/Grabacion.jsx";
import "./styles.css";

// /grabar = grabación en autoservicio para las personas sordas; cualquier otra ruta = ventanilla.
const Pantalla = window.location.pathname.replace(/\/+$/, "") === "/grabar" ? Grabacion : App;

createRoot(document.getElementById("root")).render(<Pantalla />);
