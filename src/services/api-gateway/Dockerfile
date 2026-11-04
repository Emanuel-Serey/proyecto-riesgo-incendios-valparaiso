FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --create-home app

COPY --chown=10001:10001 src/services/api-gateway/main.py ./main.py

USER 10001:10001

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]