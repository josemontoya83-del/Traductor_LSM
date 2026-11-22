-- ========================================================
-- SCHEMA BASE DE DATOS: PROYECTO TRADUCCIÓN DE SEÑAS (P1)
-- ========================================================

-- 1. Tabla de Usuarios
CREATE TABLE usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Categorías del Diccionario
CREATE TABLE diccionario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_categoria VARCHAR(100) NOT NULL,
    descripcion TEXT
);

-- 3. Tabla de Señas
CREATE TABLE sena (
    id INT AUTO_INCREMENT PRIMARY KEY,
    diccionario_id INT NOT NULL,
    palabra VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (diccionario_id) REFERENCES diccionario(id) ON DELETE CASCADE
);

-- 4. Tabla de Sesiones de Traducción
CREATE TABLE sesion_traduccion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(50) DEFAULT 'en_proceso',
    FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE
);

-- 5. Tabla de Clips de Video
CREATE TABLE video_clip (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sena_id INT NULL,
    sesion_id INT NOT NULL,
    url_video VARCHAR(255) NOT NULL,
    duracion_segundos FLOAT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sena_id) REFERENCES sena(id) ON DELETE SET NULL,
    FOREIGN KEY (sesion_id) REFERENCES sesion_traduccion(id) ON DELETE CASCADE
);

-- ========================================================
-- ÍNDICES DE OPTIMIZACIÓN Y BÚSQUEDA RÁPIDA
-- ========================================================
CREATE INDEX idx_sena_categoria ON sena(diccionario_id);
CREATE INDEX idx_sesion_fecha ON sesion_traduccion(fecha_inicio);
CREATE INDEX idx_usuario_email ON usuario(email);