import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text, URL
from sqlalchemy.exc import SQLAlchemyError


url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME")
)

engine = create_engine(
    url,
    pool_pre_ping=True
)

app = FastAPI(
    title="Data Service - Incendios Forestales",
    version="1.0"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/variables/{comuna}")
def obtener_variables(comuna: str):

    consulta = text("""
        SELECT
            temperatura_media,
            humedad_media,
            viento_medio,
            vegetacion_cobertura,
            incendios_historicos
        FROM dataset_modelo_diario
        WHERE LOWER(comuna) = LOWER(:comuna)
        ORDER BY fecha_objetivo DESC
        LIMIT 1
    """)

    try:
        with engine.connect() as conexion:
            resultado = conexion.execute(
                consulta,
                {"comuna": comuna}
            ).mappings().first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Error al consultar la base de datos"
        )

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Comuna no encontrada"
        )

    return dict(resultado)