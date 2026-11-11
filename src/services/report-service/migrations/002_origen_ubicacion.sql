ALTER TABLE public.reportes_ciudadanos
ADD COLUMN IF NOT EXISTS origen_ubicacion VARCHAR(20)
NOT NULL DEFAULT 'gps';


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_reportes_origen_ubicacion'
    ) THEN

        ALTER TABLE public.reportes_ciudadanos
        ADD CONSTRAINT chk_reportes_origen_ubicacion
        CHECK (
            origen_ubicacion IN ('gps', 'manual')
        );

    END IF;
END
$$;


UPDATE public.reportes_ciudadanos
SET origen_ubicacion = 'gps'
WHERE origen_ubicacion IS NULL;