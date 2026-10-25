#!/usr/bin/env python3
# Worker — processes jobs from a Redis queue.
import os
import json
import time
import signal
import redis
import logging
from typing import Dict, Any

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "jobs")
APP_NAME = os.getenv("APP_NAME", "worker")
VERSION = os.getenv("VERSION", "1.0.0")

# Graceful shutdown
shutting_down = False

def shutdown_handler(signum, frame):
    global shutting_down
    logger.info("shutdown_signal_received", extra={"signal": signum})
    shutting_down = True

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

def process_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single job. Override this with actual work."""
    job_type = job_data.get("type", "unknown")
    payload = job_data.get("payload", {})
    logger.info("processing_job", extra={"job_type": job_type, "payload": payload})
    # Simulate work
    time.sleep(1)
    return {"status": "completed", "result": f"processed {job_type}"}

def main():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("worker_starting", extra={
        "app": APP_NAME,
        "version": VERSION,
        "redis": REDIS_URL,
        "queue": QUEUE_NAME
    })

    while not shutting_down:
        try:
            # Blocking pop with timeout
            result = r.blpop(QUEUE_NAME, timeout=5)
            if result:
                _, job_json = result
                job = json.loads(job_json)
                result = process_job(job)
                logger.info("job_completed", extra={"result": result})
        except redis.ConnectionError as e:
            logger.error("redis_connection_error", extra={"error": str(e)})
            time.sleep(5)
        except Exception as e:
            logger.error("worker_error", extra={"error": str(e)})
            time.sleep(1)

    logger.info("worker_shutting_down")

if __name__ == "__main__":
    main()