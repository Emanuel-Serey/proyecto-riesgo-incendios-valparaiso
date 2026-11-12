FROM python:3.11-slim

WORKDIR /app

COPY src/services/report-service/requirements.txt ./requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        torch \
        torchvision \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --create-home app

COPY --chown=10001:10001 \
    src/services/report-service/main.py \
    ./main.py

COPY --chown=10001:10001 \
    frontend/public/data/region_valparaiso.geojson \
    ./region_valparaiso.geojson

RUN mkdir -p /app/data/reportes \
    && chown -R 10001:10001 /app/data

USER 10001:10001

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]