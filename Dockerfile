FROM node:22-alpine AS ui
WORKDIR /ui
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AGNI_CLOUD=1

COPY pyproject.toml README.md LICENSE ./
COPY agni ./agni
COPY runs ./runs
COPY data ./data
COPY --from=ui /ui/dist ./web/dist

RUN pip install --no-cache-dir -e . && pip install --no-cache-dir openai

EXPOSE 8000
CMD ["sh", "-c", "uvicorn agni.server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
