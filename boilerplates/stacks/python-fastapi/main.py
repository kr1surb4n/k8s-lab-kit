# Minimal FastAPI app with health endpoint, structured logging, and graceful shutdown.
# Designed for k8s: graceful shutdown, health/ready endpoints, env config.
import os
import signal
import sys
import logging
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# Structured JSON logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        return json.dumps(log_obj)

# Configure logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    app_name: str = "python-fastapi"
    version: str = "1.0.0"
    port: int = 8000
    app_env: str = "lab"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Graceful shutdown handling
shutting_down = False

def shutdown_handler(signum, frame):
    global shutting_down
    logger.info("shutdown_signal_received", extra={"signal": signum})
    shutting_down = True

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("application_starting", extra={
        "app": settings.app_name,
        "version": settings.version,
        "env": settings.app_env
    })
    yield
    # Shutdown
    logger.info("application_shutting_down", extra={"app": settings.app_name})

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "prod" else None,
    redoc_url=None
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info("http_request", extra={
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration, 2),
        "client": request.client.host if request.client else "unknown"
    })
    return response

# Health endpoint for k8s probes
@app.get("/healthz", response_model=dict)
async def healthz():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "hostname": os.uname().nodename,
        "uptime": "N/A",  # Could track startup time
    }

# Readiness endpoint
@app.get("/ready", response_model=dict)
async def ready():
    # Add dependency checks here (DB, cache, external services)
    return {"status": "ready", "app": settings.app_name}

# Example API endpoint
@app.get("/api/hello")
async def hello():
    return {
        "message": f"Hello from {settings.app_name}",
        "version": settings.version,
        "env": settings.app_env,
        "hostname": os.uname().nodename
    }

# Example with request body
class EchoRequest(BaseModel):
    message: str

@app.post("/api/echo")
async def echo(req: EchoRequest):
    return {"echo": req.message, "app": settings.app_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        workers=2,
        log_config=None,  # Use our custom logging
        access_log=False
    )