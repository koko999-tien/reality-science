# Multi-stage Dockerfile for Isolated Compute Worker (Zone 3)
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY shared/ /build/shared/
COPY worker/ /build/worker/
RUN pip install --no-cache-dir --prefix=/install /build/shared /build/worker

FROM python:3.11-slim AS runner

WORKDIR /app

# Hardening: create unprivileged user with UID:GID 10001:10001
RUN groupadd -g 10001 worker && \
    useradd -u 10001 -g worker -d /app -s /bin/false -M worker

COPY --from=builder /install /usr/local
COPY worker/worker /app/worker

USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "-Q", "compute_tasks", "--concurrency=1"]
