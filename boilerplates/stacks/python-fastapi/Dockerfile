# Python/FastAPI boilerplate — minimal production image.
#
# Build: docker build -t boilerplate/python-fastapi:1.0 boilerplates/stacks/python-fastapi
# Run:   docker run -p 8000:8000 boilerplate/python-fastapi:1.0
#
# Multi-stage: build dependencies in builder, copy only runtime to final.
FROM python:3.12-alpine AS builder
WORKDIR /app
# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-alpine
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
# Non-root user
RUN addgroup -g 1001 -S appgroup && adduser -S -u 1001 -G appgroup appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000
# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]