#!/usr/bin/env python3
# Cron job — scheduled tasks using APScheduler.
import os
import json
import signal
import logging
import redis
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "jobs")
APP_NAME = os.getenv("APP_NAME", "cron")
VERSION = os.getenv("VERSION", "1.0.0")

shutting_down = False

def shutdown_handler(signum, frame):
    global shutting_down
    logger.info("shutdown_signal_received", extra={"signal": signum})
    shutting_down = True
    if scheduler.running:
        scheduler.shutdown(wait=False)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

scheduler = BlockingScheduler()
r = redis.from_url(REDIS_URL, decode_responses=True)

def enqueue_job(job_type: str, payload: dict):
    job = {"type": job_type, "payload": payload, "enqueued_at": datetime.utcnow().isoformat()}
    r.rpush(QUEUE_NAME, json.dumps(job))
    logger.info("job_enqueued", extra={"job_type": job_type, "queue": QUEUE_NAME})

# Example scheduled jobs
@scheduler.scheduled_job('interval', minutes=5, id='heartbeat')
def heartbeat_job():
    enqueue_job("heartbeat", {"source": "cron", "time": datetime.utcnow().isoformat()})

@scheduler.scheduled_job('cron', hour=2, minute=0, id='daily_cleanup')
def daily_cleanup_job():
    enqueue_job("cleanup", {"scope": "daily", "time": datetime.utcnow().isoformat()})

def main():
    logger.info("cron_starting", extra={
        "app": APP_NAME,
        "version": VERSION,
        "redis": REDIS_URL,
        "queue": QUEUE_NAME
    })
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("cron_shutting_down")

if __name__ == "__main__":
    main()