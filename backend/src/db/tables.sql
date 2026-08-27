
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
    foto_perfil_url VARCHAR(255),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- EMPRESA
-- ============================================================
CREATE TABLE Empresa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    industria VARCHAR(100),
    sitio_web VARCHAR(255),
    foto_perfil_url VARCHAR(255)
);

CREATE TYPE rol_empresa AS ENUM ('OWNER', 'RECRUITER', 'COLLABORATOR');

CREATE TABLE empresa_usuario (
    empresa_id INT NOT NULL,
    usuario_id INT NOT NULL,
    rol rol_empresa NOT NULL,

    PRIMARY KEY (empresa_id, usuario_id),

    FOREIGN KEY (empresa_id) REFERENCES Empresa(id),
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id)
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
-- COMENTARIOS Y RESPUESTAS
-- ============================================================
CREATE TABLE comentario (
    id SERIAL PRIMARY KEY,
    publicacion_id INT NOT NULL,
    usuario_id INT NOT NULL,
    contenido VARCHAR(1000) NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    comentario_padre_id INT,

    FOREIGN KEY (publicacion_id) REFERENCES Publicacion(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (comentario_padre_id) REFERENCES comentario(id) ON DELETE CASCADE,

    CONSTRAINT comentario_contenido_check
        CHECK (LENGTH(TRIM(contenido)) BETWEEN 1 AND 1000)
);

CREATE INDEX idx_comentario_publicacion_fecha
    ON comentario (publicacion_id, fecha DESC, id DESC);
CREATE INDEX idx_comentario_padre_fecha
    ON comentario (comentario_padre_id, fecha, id);

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

-- ============================================================
-- NOTIFICACION
-- ============================================================
CREATE TABLE notificacion (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    mensaje VARCHAR(500) NOT NULL,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    postulacion_id INT,
    oferta_id INT,
    usuario_origen_id INT,

    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
    FOREIGN KEY (postulacion_id) REFERENCES Postulacion(id),
    FOREIGN KEY (oferta_id) REFERENCES Oferta(id),
    FOREIGN KEY (usuario_origen_id) REFERENCES Usuario(id),

    CONSTRAINT notificacion_tipo_check CHECK (
        tipo IN (
            'POSTULACION_NUEVA',
            'POSTULACION_ESTADO',
            'NUEVO_SEGUIDOR',
            'NUEVA_INVITACION_CONEXION',
            'CONEXION_ACEPTADA'
        )
    )
);

CREATE INDEX idx_notificacion_usuario_fecha
    ON notificacion (usuario_id, fecha DESC);

-- ============================================================
-- SEGUIMIENTO (N a M DIRECCIONAL)
-- ============================================================
CREATE TABLE seguimiento (
    seguidor_id INT NOT NULL,
    seguido_id INT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (seguidor_id, seguido_id),

    FOREIGN KEY (seguidor_id) REFERENCES Usuario(id),
    FOREIGN KEY (seguido_id) REFERENCES Usuario(id),

    CHECK (seguidor_id <> seguido_id)
);

-- ============================================================
-- MENSAJES PRIVADOS 1 A 1
-- ============================================================
CREATE TABLE conversacion (
    id SERIAL PRIMARY KEY,
    usuario_menor_id INT NOT NULL,
    usuario_mayor_id INT NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_ultimo_mensaje TIMESTAMP,

    FOREIGN KEY (usuario_menor_id) REFERENCES Usuario(id),
    FOREIGN KEY (usuario_mayor_id) REFERENCES Usuario(id),
    CONSTRAINT conversacion_par_ordenado_check
        CHECK (usuario_menor_id < usuario_mayor_id),
    CONSTRAINT uq_conversacion_par_privado
        UNIQUE (usuario_menor_id, usuario_mayor_id)
);

CREATE TABLE conversacion_usuario (
    conversacion_id INT NOT NULL,
    usuario_id INT NOT NULL,
    ultima_lectura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (conversacion_id, usuario_id),
    FOREIGN KEY (conversacion_id) REFERENCES conversacion(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id) ON DELETE CASCADE
);

CREATE TABLE mensaje (
    id SERIAL PRIMARY KEY,
    conversacion_id INT NOT NULL,
    autor_id INT NOT NULL,
    contenido VARCHAR(2000) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'TEXTO',
    publicacion_id INT,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (conversacion_id) REFERENCES conversacion(id) ON DELETE CASCADE,
    FOREIGN KEY (publicacion_id) REFERENCES Publicacion(id) ON DELETE SET NULL,
    CONSTRAINT fk_mensaje_autor_participante
        FOREIGN KEY (conversacion_id, autor_id)
        REFERENCES conversacion_usuario(conversacion_id, usuario_id)
        ON DELETE CASCADE,
    CONSTRAINT mensaje_contenido_check
        CHECK (length(trim(contenido)) BETWEEN 1 AND 2000),
    CONSTRAINT mensaje_tipo_check
        CHECK (tipo IN ('TEXTO', 'PUBLICACION')),
    CONSTRAINT mensaje_publicacion_tipo_check
        CHECK (tipo = 'PUBLICACION' OR publicacion_id IS NULL)
);

CREATE INDEX idx_conversacion_ultimo_mensaje
    ON conversacion (fecha_ultimo_mensaje);
CREATE INDEX idx_conversacion_usuario_usuario
    ON conversacion_usuario (usuario_id, conversacion_id);
CREATE INDEX idx_mensaje_conversacion_fecha
    ON mensaje (conversacion_id, fecha, id);
CREATE INDEX idx_mensaje_publicacion
    ON mensaje (publicacion_id);
