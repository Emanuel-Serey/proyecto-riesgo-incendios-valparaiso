-- =========================================================
-- 003_ciclo_vida_reportes.sql
-- Agrega ciclo de vida para reportes confirmados:
-- pendiente -> confirmado -> resuelto
-- =========================================================

ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS fecha_validacion TIMESTAMPTZ;

ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS fecha_resolucion TIMESTAMPTZ;


-- El CHECK original fue creado sin nombre explícito,
-- por lo que PostgreSQL normalmente lo llama:
-- reportes_ciudadanos_estado_check
ALTER TABLE public.reportes_ciudadanos
DROP CONSTRAINT IF EXISTS reportes_ciudadanos_estado_check;


-- Fallback por si el constraint tiene otro nombre.
DO $$
DECLARE
    nombre_constraint TEXT;
BEGIN
    SELECT c.conname
    INTO nombre_constraint
    FROM pg_constraint c
    JOIN pg_class t
        ON t.oid = c.conrelid
    JOIN pg_namespace n
        ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relname = 'reportes_ciudadanos'
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) ILIKE '%estado%'
    LIMIT 1;

    IF nombre_constraint IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE public.reportes_ciudadanos DROP CONSTRAINT %I',
            nombre_constraint
        );
    END IF;
END
$$;


ALTER TABLE public.reportes_ciudadanos
ADD CONSTRAINT reportes_ciudadanos_estado_check
CHECK (
    estado IN (
        'pendiente',
        'confirmado',
        'rechazado',
        'resuelto'
    )
);
