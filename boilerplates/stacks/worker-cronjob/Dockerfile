# Worker + CronJob boilerplate — Python worker with scheduled tasks.
#
# Build: docker build -t boilerplate/worker-cron:1.0 boilerplates/stacks/worker-cronjob
# Run (worker): docker run boilerplate/worker-cron:1.0 python worker.py
# Run (cron):   docker run boilerplate/worker-cron:1.0 python cron.py
#
# Multi-stage: install deps in builder, copy to final.
FROM python:3.12-alpine AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-alpine
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN addgroup -g 1001 -S appgroup && adduser -S -u 1001 -G appgroup appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .
USER appuser
# Entry point decides: worker.py or cron.py
ENTRYPOINT ["python"]