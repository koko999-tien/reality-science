# Multi-stage Dockerfile for FastAPI Modular Monolith (Zone 2)
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY shared/ /build/shared/
COPY backend/ /build/backend/
RUN pip install --no-cache-dir --prefix=/install /build/shared /build/backend

FROM python:3.11-slim AS runner

WORKDIR /app

# Non-root user with UID:GID 10001:10001
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -d /app -s /bin/false -M appuser

COPY --from=builder /install /usr/local
COPY backend/app /app/app
COPY backend/alembic.ini /app/alembic.ini

USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
