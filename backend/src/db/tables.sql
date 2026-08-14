
-- ============================================================
-- USUARIO
-- ============================================================
CREATE TABLE Usuario (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    headline VARCHAR(200) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- EMPRESA
-- ============================================================
CREATE TABLE Empresa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    industria VARCHAR(100),
    sitio_web VARCHAR(255)
);

-- ============================================================
-- EXPERIENCIA
-- ============================================================
CREATE TABLE Experiencia (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL,
    empresa_id INT NOT NULL,
    puesto VARCHAR(100) NOT NULL,
    desde DATE NOT NULL,
    hasta DATE,

    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
    FOREIGN KEY (empresa_id) REFERENCES Empresa(id),

    CHECK (hasta IS NULL OR desde <= hasta)
);

-- ============================================================
-- PUBLICACION
-- ============================================================
CREATE TABLE Publicacion (
    id SERIAL PRIMARY KEY,
    autor_id INT NOT NULL,
    texto VARCHAR(3000) NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (autor_id) REFERENCES Usuario(id),

    CHECK (LENGTH(texto) BETWEEN 1 AND 3000)
);

-- ============================================================
-- OFERTAd
-- ============================================================
CREATE TABLE Oferta (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    publicada BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_publicacion TIMESTAMP,

    FOREIGN KEY (empresa_id) REFERENCES Empresa(id)
);

-- ============================================================
-- POSTULACION
-- ============================================================
CREATE TABLE Postulacion (
    id SERIAL PRIMARY KEY,
    oferta_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'nueva',

    FOREIGN KEY (oferta_id) REFERENCES Oferta(id),
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),

    UNIQUE (oferta_id, usuario_id),

    CHECK (estado IN (
        'nueva',
        'vista',
        'entrevista',
        'contratado',
        'rechazada'
    ))
);

-- ============================================================
-- CONEXIONES (N a M)
-- ============================================================
CREATE TABLE conexiones (
    usuario_a INT NOT NULL,
    usuario_b INT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',

    PRIMARY KEY (usuario_a, usuario_b),

    FOREIGN KEY (usuario_a) REFERENCES Usuario(id),
    FOREIGN KEY (usuario_b) REFERENCES Usuario(id),

    CHECK (usuario_a <> usuario_b),

    CHECK (estado IN (
        'pendiente',
        'aceptada',
        'rechazada'
    ))
);

-- ============================================================
-- REACCIONES (N a M)
-- ============================================================
CREATE TABLE reacciones (
    usuario_id INT NOT NULL,
    publicacion_id INT NOT NULL,
    tipo VARCHAR(20) NOT NULL,

    PRIMARY KEY (usuario_id, publicacion_id),

    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
    FOREIGN KEY (publicacion_id) REFERENCES Publicacion(id),

    CHECK (tipo IN (
        'like',
        'celebrar',
        'apoyar',
        'interesante'
    ))
);