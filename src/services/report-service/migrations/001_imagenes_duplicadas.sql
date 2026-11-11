-- =========================================================
-- DETECCIÓN DE FOTOGRAFÍAS DUPLICADAS
-- Report Service
-- =========================================================

ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS imagen_phash VARCHAR(16);


ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS posible_duplicado BOOLEAN
NOT NULL DEFAULT FALSE;


ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS reporte_duplicado_id BIGINT;


ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS distancia_phash INTEGER;


CREATE INDEX IF NOT EXISTS idx_reportes_imagen_phash
ON public.reportes_ciudadanos (
    imagen_phash
);