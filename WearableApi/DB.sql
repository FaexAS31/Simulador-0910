-- ==========================================================
-- STEP 1: BASE TABLES (Only PKs, timestamps, and trigger setup)
-- ==========================================================

-- 1.1 Universal function for updated_at management
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ==========================================================
-- 1.2 Core parent table: Usuarios
-- ==========================================================
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TRIGGER trg_usuarios_update_timestamp
BEFORE UPDATE ON usuarios
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Instead of VARCHAR for controlled values:
CREATE TYPE rol_type AS ENUM ('consumidor', 'administrador');

ALTER TABLE usuarios ALTER COLUMN rol TYPE rol_type USING rol::rol_type;

ALTER TABLE usuarios
ADD CONSTRAINT check_email_format 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
-- ==========================================================
-- 1.3 Lookup tables (controlled vocabularies)
-- ==========================================================

-- Emociones lookup
CREATE TABLE emociones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TRIGGER trg_emociones_update_timestamp
BEFORE UPDATE ON emociones
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- Motivos lookup
CREATE TABLE motivos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TRIGGER trg_motivos_update_timestamp
BEFORE UPDATE ON motivos
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- Soluciones lookup
CREATE TABLE soluciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TRIGGER trg_soluciones_update_timestamp
BEFORE UPDATE ON soluciones
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


-- Hábitos lookup
CREATE TABLE habitos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TRIGGER trg_habitos_update_timestamp
BEFORE UPDATE ON habitos
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

llllll
ALTER TABLE formularios 
ADD COLUMN habitos JSONB;
-- ==========================================================
-- 1.4 Permisos base table
-- ==========================================================
CREATE TABLE permisos (
    id SERIAL PRIMARY KEY,
    lectura BOOLEAN DEFAULT TRUE,
    creacion BOOLEAN DEFAULT FALSE,
    edicion BOOLEAN DEFAULT FALSE,
    eliminacion BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TRIGGER trg_permisos_update_timestamp
BEFORE UPDATE ON permisos
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- ==========================================================
-- Notes
-- ==========================================================
-- • Each table above has only its own PK.
-- • All include automatic timestamps and a trigger for updated_at.
-- • Lookup tables (emociones, motivos, soluciones, habitos) will
--   later be referenced from form and behavior entities.
-- • No foreign keys yet—these will be defined in Step 2.
-- • Class-table inheritance for administradores/consumidores
--   will reference usuarios(id) in the next step.

-- ==========================================================
-- STEP 2: TABLES WITH FK RELATIONS TO BASE TABLES
-- ==========================================================

-- ==========================================================
-- 2.1 Administradores (inherits from Usuarios)
-- One-to-one relation with usuarios
-- ==========================================================
CREATE TABLE administradores (
    id SERIAL PRIMARY KEY,
    usuario_id INT UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    area_responsable VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index on FK
CREATE INDEX idx_administradores_usuario_id
    ON administradores(usuario_id);

CREATE TRIGGER trg_administradores_update_timestamp
BEFORE UPDATE ON administradores
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Each administrador corresponds to exactly one usuario (1:1)
-- Deleting the usuario removes the administrador automatically


-- ==========================================================
-- 2.2 Consumidores (inherits from Usuarios)
-- One-to-one relation with usuarios
-- ==========================================================
CREATE TABLE consumidores (
    id SERIAL PRIMARY KEY,
    usuario_id INT UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    edad INT,
    peso FLOAT,
	altura FLOAT,
	bmi FLOAT,  -- Regular column, will be auto-calculated by trigger
	genero VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE consumidores
ALTER COLUMN genero DROP NOT NULL;

CREATE INDEX idx_consumidores_usuario_id
    ON consumidores(usuario_id);

-- Function to auto-calculate BMI (Django ORM compatible)
CREATE OR REPLACE FUNCTION calculate_bmi()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.peso IS NOT NULL AND NEW.altura IS NOT NULL AND NEW.altura > 0 THEN
        NEW.bmi := ROUND((NEW.peso / POWER(NEW.altura / 100, 2))::numeric, 2);
    ELSE
        NEW.bmi := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to calculate BMI before insert/update
CREATE TRIGGER trigger_calculate_bmi
    BEFORE INSERT OR UPDATE OF peso, altura
    ON consumidores
    FOR EACH ROW
    EXECUTE FUNCTION calculate_bmi();

CREATE TRIGGER trg_consumidores_update_timestamp
BEFORE UPDATE ON consumidores
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TYPE genero_type AS ENUM ('masculino', 'femenino');
ALTER TABLE consumidores ALTER COLUMN genero TYPE genero_type USING genero::genero_type;

-- Each consumidor corresponds to exactly one usuario (1:1)
-- Deleting the usuario removes the consumidor automatically


-- ==========================================================
-- 2.3 Formularios
-- Each formulario belongs to a consumidor (1:N)
-- ==========================================================
CREATE TABLE formularios (
    id SERIAL PRIMARY KEY,
    consumidor_id INT
        REFERENCES consumidores(id)
        ON DELETE CASCADE,
    fecha_envio TIMESTAMP DEFAULT NOW(),
    habito_id INT
        REFERENCES habitos(id)
        ON DELETE SET NULL,
    emociones JSONB,  -- optional dynamic data
    motivos JSONB,
    soluciones JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_formularios_consumidor_id
    ON formularios(consumidor_id);
CREATE INDEX idx_formularios_habito_id
    ON formularios(habito_id);

CREATE TRIGGER trg_formularios_update_timestamp
BEFORE UPDATE ON formularios
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- A consumidor can fill many formularios (1:N)
-- Deleting a consumidor removes all its formularios


-- ==========================================================
-- 2.4 Formularios Temporales
-- Event-driven or model-triggered forms related to consumidores
-- ==========================================================
CREATE TABLE formularios_temporales (
    id SERIAL PRIMARY KEY,
    consumidor_id INT REFERENCES consumidores(id) ON DELETE CASCADE,
    emociones JSONB,  
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_formularios_temporales_consumidor_id
    ON formularios_temporales(consumidor_id);

CREATE TRIGGER trg_formularios_temporales_update_timestamp
BEFORE UPDATE ON formularios_temporales
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Each consumidor may have several temporary forms (1:N)
-- Deleting the consumidor cascades to remove those forms


-- Comments:
-- • Each linking table enforces many-to-many between formularios and lookup vocabularies.
-- • Deleting a formulario or the related lookup entry removes the mapping automatically.


-- ==========================================================
-- STEP 3: SENSOR, ANALYSIS, AND EVENT TABLES
-- ==========================================================


-- ==========================================================
-- 3.1 Ventanas
-- A window of aggregated sensor readings for one consumidor
-- ==========================================================
CREATE TABLE ventanas (
    id SERIAL PRIMARY KEY,
    consumidor_id INT
        REFERENCES consumidores(id)
        ON DELETE CASCADE,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    hr_mean FLOAT,
    hr_std FLOAT,
    gyro_energy FLOAT,
    accel_energy FLOAT,
    emotion_embedding JSONB,   -- vector representation from model
    motive_embedding JSONB,
    solution_embedding JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ventanas_consumidor_id ON ventanas(consumidor_id);
CREATE INDEX idx_ventanas_window_start ON ventanas(window_start);
CREATE INDEX idx_ventanas_window_end ON ventanas(window_end);
CREATE INDEX idx_ventanas_emotion_embedding
    ON ventanas USING gin(emotion_embedding jsonb_path_ops);
CREATE INDEX idx_ventanas_motive_embedding
    ON ventanas USING gin(motive_embedding jsonb_path_ops);
CREATE INDEX idx_ventanas_solution_embedding
    ON ventanas USING gin(solution_embedding jsonb_path_ops);

CREATE TRIGGER trg_ventanas_update_timestamp
BEFORE UPDATE ON ventanas
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Each consumidor can have multiple ventanas (1:N)
-- Deleting a consumidor removes its ventanas automatically


-- ==========================================================
-- 3.2 Lecturas
-- ==========================================================

CREATE TABLE lecturas (
    id SERIAL PRIMARY KEY,
    ventana_id INT
        REFERENCES ventanas(id)
        ON DELETE CASCADE,
    heart_rate FLOAT,
    accel_x FLOAT,
    accel_y FLOAT,
    accel_z FLOAT,
    gyro_x FLOAT,
    gyro_y FLOAT,
    gyro_z FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lecturas_ventana_id ON lecturas(ventana_id);

CREATE TRIGGER trg_lecturas_update_timestamp
BEFORE UPDATE ON lecturas
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Each ventana can include many lecturas (1:N)
-- Deleting a ventana cascades deletion of its lecturas


-- ==========================================================
-- 3.3 Analisis
-- Stores the output of ML model predictions per ventana
-- ==========================================================
CREATE TABLE analisis (
    id SERIAL PRIMARY KEY,
    ventana_id INT
        REFERENCES ventanas(id)
        ON DELETE CASCADE,
    modelo_usado VARCHAR(100),
    probabilidad_modelo FLOAT,
    urge_label INT,  
    recall FLOAT,
    f1_score FLOAT,
    accuracy FLOAT,
    roc_auc FLOAT,
    comentario_modelo TEXT,
    feature_importance JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analisis_ventana_id ON analisis(ventana_id);
CREATE INDEX idx_analisis_probabilidad_modelo ON analisis(probabilidad_modelo);

CREATE TRIGGER trg_analisis_update_timestamp
BEFORE UPDATE ON analisis
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

ALTER TABLE analisis
ADD CONSTRAINT check_urge_label CHECK (urge_label IN (0, 1));

-- Each ventana has one or more analyses (1:N)
-- Deleting a ventana cascades to remove its analyses


-- ==========================================================
-- 3.4 Deseos
-- ==========================================================

CREATE TABLE deseos (
    id SERIAL PRIMARY KEY,
    consumidor_id INT
        REFERENCES consumidores(id)
        ON DELETE CASCADE,
    ventana_id INT
        REFERENCES ventanas(id)
        ON DELETE SET NULL,
    tipo VARCHAR(50),
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deseos_consumidor_id ON deseos(consumidor_id);
CREATE INDEX idx_deseos_ventana_id ON deseos(ventana_id);

CREATE TRIGGER trg_deseos_update_timestamp
BEFORE UPDATE ON deseos
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TYPE deseo_tipo AS ENUM ('comida', 'bebida', 'compra', 'sustancia', 'otro');

-- Then update the tables:
ALTER TABLE deseos ALTER COLUMN tipo TYPE deseo_tipo USING tipo::deseo_tipo;

-- Each consumidor can have many deseos (1:N)
-- Deleting a consumidor cascades deletion of deseos
-- If a related ventana is deleted, ventana_id is set NULL


-- ==========================================================
-- 3.5 Notificaciones
-- Sent to consumidores in response to eventos or deseos
-- ==========================================================
CREATE TABLE notificaciones (
    id SERIAL PRIMARY KEY,
    consumidor_id INT
        REFERENCES consumidores(id)
        ON DELETE CASCADE,
    deseo_id INT
        REFERENCES deseos(id)
        ON DELETE SET NULL,
    tipo VARCHAR(50),              -- e.g. 'recomendacion', 'alerta'
    contenido TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT NOW(),
    leida BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notificaciones_consumidor_id ON notificaciones(consumidor_id);
CREATE INDEX idx_notificaciones_deseo_id ON notificaciones(deseo_id);
CREATE INDEX idx_notificaciones_fecha_envio ON notificaciones(fecha_envio);

CREATE TRIGGER trg_notificaciones_update_timestamp
BEFORE UPDATE ON notificaciones
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TYPE notificacion_tipo AS ENUM ('recomendacion', 'alerta', 'recordatorio', 'logro');
ALTER TABLE notificaciones ALTER COLUMN tipo TYPE notificacion_tipo USING tipo::notificacion_tipo;

-- Each consumidor can receive many notificaciones (1:N)
-- Deleting a consumidor removes related notificaciones
-- Deleting a deseo sets deseo_id to NULL

-- These constraints:
ALTER TABLE consumidores
ADD CONSTRAINT check_edad_positive CHECK (edad > 0 AND edad < 150),
ADD CONSTRAINT check_peso_positive CHECK (peso > 0),
ADD CONSTRAINT check_altura_positive CHECK (altura > 0);

ALTER TABLE ventanas
ADD CONSTRAINT check_window_order CHECK (window_end > window_start);

ALTER TABLE analisis
ADD CONSTRAINT check_probabilidad_range CHECK (probabilidad_modelo BETWEEN 0 AND 1),
ADD CONSTRAINT check_metrics_range CHECK (
    recall BETWEEN 0 AND 1 AND
    f1_score BETWEEN 0 AND 1 AND
    accuracy BETWEEN 0 AND 1 AND
    roc_auc BETWEEN 0 AND 1
);

-- Better query performance:
CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_rol ON usuarios(rol);
CREATE INDEX idx_formularios_fecha_envio ON formularios(fecha_envio);
CREATE INDEX idx_notificaciones_leida ON notificaciones(leida) WHERE leida = FALSE;

-- Step 1: Drop the generated column
ALTER TABLE consumidores DROP COLUMN bmi;

-- Step 2: Add it back as a regular nullable column
ALTER TABLE consumidores ADD COLUMN bmi FLOAT;

-- Step 3: Create a function to calculate BMI
CREATE OR REPLACE FUNCTION calculate_bmi()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.peso IS NOT NULL AND NEW.altura IS NOT NULL AND NEW.altura > 0 THEN
        NEW.bmi := ROUND((NEW.peso / POWER(NEW.altura / 100, 2))::numeric, 2);
    ELSE
        NEW.bmi := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create trigger to auto-calculate BMI on INSERT/UPDATE
DROP TRIGGER IF EXISTS trigger_calculate_bmi ON consumidores;

CREATE TRIGGER trigger_calculate_bmi
    BEFORE INSERT OR UPDATE OF peso, altura
    ON consumidores
    FOR EACH ROW
    EXECUTE FUNCTION calculate_bmi();