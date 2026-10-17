FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/services/risk-service/main.py ./main.py

COPY models/random_forest_incendios.joblib ./models/random_forest_incendios.joblib

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]