FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AGNI_CLOUD=1

COPY pyproject.toml README.md LICENSE ./
COPY agni ./agni
COPY web ./web
COPY runs ./runs
COPY data ./data

RUN pip install --no-cache-dir -e . && pip install --no-cache-dir openai

EXPOSE 8000
CMD ["sh", "-c", "uvicorn agni.server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
