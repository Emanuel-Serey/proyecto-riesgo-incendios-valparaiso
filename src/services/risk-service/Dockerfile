FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

COPY --chown=app:app src/services/risk-service/main.py ./main.py
COPY --chown=app:app models/random_forest_incendios.joblib ./models/random_forest_incendios.joblib

USER app

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]