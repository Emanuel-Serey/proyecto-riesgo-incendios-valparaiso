FROM python:3.12-slim


WORKDIR /app


RUN groupadd \
        --gid 10001 \
        appgroup \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        appuser


COPY src/etl/requirements.txt /tmp/requirements.txt


RUN pip install \
    --no-cache-dir \
    -r /tmp/requirements.txt


# =========================================================
# CÓDIGO ETL
# =========================================================

COPY --chown=10001:10001 \
    src/etl \
    /app/src/etl


# =========================================================
# GEOJSON DE COMUNAS
# =========================================================

COPY --chown=10001:10001 \
    frontend/public/data/comunas_valparaiso.geojson \
    /app/frontend/public/data/comunas_valparaiso.geojson


# =========================================================
# ARCHIVOS PROCESADOS NECESARIOS
# =========================================================

COPY --chown=10001:10001 \
    data/processed/perfil_incendios_historicos.csv \
    /app/data/processed/perfil_incendios_historicos.csv


COPY --chown=10001:10001 \
    data/processed/vegetacion_comuna.csv \
    /app/data/processed/vegetacion_comuna.csv


# =========================================================
# DIRECTORIOS DE ESCRITURA
# =========================================================

RUN mkdir -p \
        /app/data/raw/dmc/api \
        /app/data/processed \
        /app/logs \
    && chown -R \
        10001:10001 \
        /app


USER 10001:10001


CMD ["python", "src/etl/pipeline_etl.py"]