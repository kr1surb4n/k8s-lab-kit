# Minimal FastAPI app with health endpoint, structured logging, and graceful shutdown.
# Designed for k8s: graceful shutdown, health/ready endpoints, env config.
import os
import signal
import sys
import time
import logging
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Return the active trace and span ids, so logs point at the exported span.
def current_trace_ids():
    ctx = trace.get_current_span().get_span_context()
    if not ctx.is_valid:
        return None, None
    return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")


# Structured JSON logging, with the live trace id on every line.
class JsonFormatter(logging.Formatter):
    def format(self, record):
        trace_id, span_id = current_trace_ids()
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "trace_id": trace_id or getattr(record, "trace_id", None),
            "span_id": span_id or getattr(record, "span_id", None),
        }
        # Include fields passed through logging's extra= argument.
        standard = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "taskName",
            "exc_info", "exc_text", "stack_info", "trace_id", "span_id",
        }
        for key, value in record.__dict__.items():
            if key not in standard:
                log_obj[key] = value
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
    otlp_endpoint: str = (
        "http://otel-collector-opentelemetry-collector.observability:4318/v1/traces"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Send spans to the collector and wrap the app; logs pick up the same trace id.
def setup_tracing(app: FastAPI):
    resource = Resource.create({SERVICE_NAME: settings.app_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    # Keep our JSON formatter; the instrumentor only adds trace fields to records.
    LoggingInstrumentor().instrument(set_logging_format=False)

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

# Log every request with the trace id; pure ASGI keeps the span context alive.
class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()
        trace_id, span_id = current_trace_ids()
        status = 500

        # Add the trace id to the response and remember the status for the log.
        async def send_with_trace(message: Message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                if trace_id:
                    headers["X-Trace-ID"] = trace_id
            await send(message)

        await self.app(scope, receive, send_with_trace)

        duration = (time.time() - start) * 1000
        client = scope.get("client")
        logger.info("http_request", extra={
            "method": scope.get("method"),
            "path": scope.get("path"),
            "status": status,
            "duration_ms": round(duration, 2),
            "client": client[0] if client else "unknown",
            "trace_id": trace_id,
            "span_id": span_id,
        })

# Add the logger first, then OTel, so the request span wraps the logger.
app.add_middleware(RequestLoggingMiddleware)
setup_tracing(app)

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