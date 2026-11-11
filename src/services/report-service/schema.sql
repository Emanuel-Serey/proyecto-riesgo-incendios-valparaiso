CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.reportes_ciudadanos (
    id_reporte BIGSERIAL PRIMARY KEY,

    fecha_reporte TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    descripcion TEXT,

    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (
            estado IN (
                'pendiente',
                'confirmado',
                'rechazado'
            )
        ),

    ubicacion GEOGRAPHY(POINT, 4326) NOT NULL,

    precision_gps_m NUMERIC(10,2),

    imagen_url TEXT,

    yolo_detectado BOOLEAN,

    yolo_clase VARCHAR(20),

    yolo_confianza NUMERIC(5,4),

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reportes_ubicacion
ON public.reportes_ciudadanos
USING GIST (ubicacion);