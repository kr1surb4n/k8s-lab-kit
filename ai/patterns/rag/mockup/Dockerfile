# RAG API Mockup — minimal FastAPI image.
#
# Build: docker build -t boilerplate/rag-api:1.0 ai/patterns/rag/mockup
# Run:   docker run -p 8000:8000 boilerplate/rag-api:1.0
#
# Multi-stage: install deps in builder, copy to final.
FROM python:3.12-alpine AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-alpine
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN addgroup -g 1001 -S appgroup && adduser -S -u 1001 -G appgroup appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]