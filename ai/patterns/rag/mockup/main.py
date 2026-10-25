#!/usr/bin/env python3
# RAG API Mockup — minimal FastAPI demo with OTel tracing.
# Run: uvicorn main:app --host 0.0.0.0 --port 8000
import os
import time
import logging
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

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
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", "pathname",
                          "filename", "module", "lineno", "funcName", "created",
                          "msecs", "relativeCreated", "thread", "threadName",
                          "processName", "process", "trace_id", "span_id"]:
                log_obj[key] = value
        return json.dumps(log_obj)

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
logger = logging.getLogger(__name__)

# Settings
class Settings(BaseSettings):
    app_name: str = "rag-api"
    version: str = "1.0.0"
    port: int = 8000
    otlp_endpoint: str = "http://otel-collector:4318/v1/traces"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Global tracer
tracer = None

def setup_tracing():
    global tracer
    resource = Resource.create({SERVICE_NAME: settings.app_name})
    provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(settings.app_name)

    # Instrument FastAPI, HTTPX, logging
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    # Keep our JSON formatter; the instrumentor only adds trace fields to records.
    LoggingInstrumentor().instrument(set_logging_format=False)

# Mock data store (in-memory for demo)
DOCUMENTS = {
    "doc-1": {
        "id": "doc-1",
        "title": "Kubernetes Deployments",
        "text": "A Deployment manages a set of identical Pods. Use kubectl scale deploy/myapp --replicas=3 to scale.",
        "metadata": {"source": "k8s-docs", "category": "workloads"}
    },
    "doc-2": {
        "id": "doc-2",
        "title": "Kubernetes Services",
        "text": "A Service exposes a set of Pods as a network service. ClusterIP is the default type. Use LoadBalancer for external access.",
        "metadata": {"source": "k8s-docs", "category": "networking"}
    },
    "doc-3": {
        "id": "doc-3",
        "title": "Kubernetes ConfigMaps",
        "text": "A ConfigMap stores configuration data as key-value pairs. Pods can consume ConfigMaps as environment variables or mounted files.",
        "metadata": {"source": "k8s-docs", "category": "config"}
    },
    "doc-4": {
        "id": "doc-4",
        "title": "Kubernetes Secrets",
        "text": "A Secret stores sensitive data like passwords and tokens. Use stringData for raw values. Secrets are mounted as files or env vars.",
        "metadata": {"source": "k8s-docs", "category": "config"}
    },
    "doc-5": {
        "id": "doc-5",
        "title": "Scaling Deployments",
        "text": "To scale a Deployment, use kubectl scale deploy/NAME --replicas=N. The rolling update strategy ensures zero-downtime with maxUnavailable=0.",
        "metadata": {"source": "k8s-docs", "category": "operations"}
    },
}

# Pydantic models
class IngestRequest(BaseModel):
    documents: List[Dict[str, Any]]

class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True

class Source(BaseModel):
    doc_id: str
    title: str
    score: float
    snippet: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    trace_id: str
    latency_ms: int

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str

# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_starting", extra={"app": settings.app_name, "version": settings.version})
    yield
    logger.info("application_shutting_down")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Set up tracing before startup: FastAPI refuses middleware added after it starts.
setup_tracing()

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()

    # Capture the span ids now: the context is gone by the time the response returns.
    trace_id, span_id = current_trace_ids()

    # Add request details to the log context.
    extra = {"method": request.method, "path": request.url.path}

    response = await call_next(request)

    # The handler knows the real span id; prefer the header it set.
    trace_id = response.headers.get("x-trace-id") or trace_id

    duration = (time.time() - start) * 1000
    logger.info("http_request", extra={
        **extra,
        "status": response.status_code,
        "duration_ms": round(duration, 2),
        "trace_id": trace_id,
        "span_id": span_id,
    })
    # Echo the real trace id so a caller can find the trace in Tempo.
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    return response

# Health endpoint
@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok", app=settings.app_name, version=settings.version)

# Ingest endpoint (mock - just logs)
@app.post("/v1/rag/ingest")
async def ingest(request: IngestRequest):
    with tracer.start_as_current_span("rag.ingest") as span:
        span.set_attribute("doc_count", len(request.documents))
        logger.info("ingest_request", extra={"doc_count": len(request.documents)})
        # In real impl: chunk, embed, upsert to vector DB
        for doc in request.documents:
            logger.info("ingested_doc", extra={"doc_id": doc.get("id")})
        return {"status": "ok", "ingested": len(request.documents)}

# Query endpoint (mock retrieval + generation)
@app.post("/v1/rag/query", response_model=QueryResponse)
async def query(request: QueryRequest, response: Response):
    start = time.time()

    with tracer.start_as_current_span("rag.query") as span:
        # Use the span's own id, so the response and the trace agree.
        trace_id, _ = current_trace_ids()
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
        span.set_attribute("query", request.query)
        span.set_attribute("top_k", request.top_k)
        span.set_attribute("rerank", request.rerank)

        # Mock retrieval: simple keyword match
        def retrieve(q: str, k: int):
            with tracer.start_as_current_span("retrieve") as s:
                q_lower = q.lower()
                results = []
                for doc_id, doc in DOCUMENTS.items():
                    score = 0
                    for word in q_lower.split():
                        if word in doc["text"].lower():
                            score += 1
                        if word in doc["title"].lower():
                            score += 2
                    if score > 0:
                        results.append((doc_id, doc, score))
                results.sort(key=lambda x: x[2], reverse=True)
                return results[:k]

        def rerank(q: str, candidates: List):
            with tracer.start_as_current_span("rerank") as s:
                # Mock rerank: just reorder by title match
                q_words = set(q.lower().split())
                for i, (doc_id, doc, score) in enumerate(candidates):
                    title_words = set(doc["title"].lower().split())
                    overlap = len(q_words & title_words)
                    candidates[i] = (doc_id, doc, score + overlap * 0.5)
                candidates.sort(key=lambda x: x[2], reverse=True)
                return candidates[:5]

        def generate(q: str, sources: List) -> str:
            with tracer.start_as_current_span("generate") as s:
                # Mock generation: concatenate top snippets
                snippets = [s[1]["text"][:200] for s in sources]
                return f"Based on the documentation: {' '.join(snippets[:2])}"

        def guardrail(answer: str) -> str:
            with tracer.start_as_current_span("guardrail") as s:
                # Mock: just return as-is
                return answer

        # Execute pipeline
        retrieved = retrieve(request.query, request.top_k * 2)
        if request.rerank:
            retrieved = rerank(request.query, retrieved)

        sources = [
            Source(
                doc_id=doc_id,
                title=doc["title"],
                score=round(score / 10.0, 2),
                snippet=doc["text"][:150] + "..."
            )
            for doc_id, doc, score in retrieved[:request.top_k]
        ]

        answer = generate(request.query, retrieved)
        answer = guardrail(answer)

        latency = int((time.time() - start) * 1000)

        span.set_attribute("source_count", len(sources))
        span.set_attribute("latency_ms", latency)

        logger.info("query_completed", extra={
            "query": request.query,
            "sources": len(sources),
            "latency_ms": latency,
            "trace_id": trace_id
        })

        return QueryResponse(
            answer=answer,
            sources=sources,
            trace_id=trace_id,
            latency_ms=latency
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        log_config=None,
        access_log=False
    )