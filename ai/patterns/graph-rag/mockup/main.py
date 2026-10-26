#!/usr/bin/env python3
# Graph RAG API Mockup — minimal FastAPI demo with OTel tracing + AGE graph.
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

# OpenTelemetry - minimal setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
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
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", "pathname",
                          "filename", "module", "lineno", "funcName", "created",
                          "msecs", "relativeCreated", "thread", "threadName",
                          "processName", "process", "trace_id", "span_id"]:
                log_obj[key] = value
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    app_name: str = "graph-rag-api"
    version: str = "1.0.0"
    port: int = 8000
    otlp_endpoint: str = (
        "http://otel-collector-opentelemetry-collector.observability:4318/v1/traces"
    )
    log_level: str = "INFO"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
tracer = None

# Send spans to the collector; logs pick up the same trace id.
def setup_tracing():
    global tracer
    resource = Resource.create({SERVICE_NAME: settings.app_name})
    provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(settings.app_name)

# Mock graph data store
DOCUMENTS = {
    "doc-1": {
        "id": "doc-1", "title": "Kubernetes Deployments",
        "text": "A Deployment manages a set of identical Pods. Use kubectl scale deploy/myapp --replicas=3 to scale.",
        "entities": [{"name": "Deployment", "type": "Resource"}, {"name": "Pod", "type": "Resource"}, {"name": "ReplicaSet", "type": "Resource"}],
        "relations": [{"source": "Deployment", "type": "MANAGES", "target": "ReplicaSet"}, {"source": "ReplicaSet", "type": "CREATES", "target": "Pod"}]
    },
    "doc-2": {
        "id": "doc-2", "title": "Kubernetes Services",
        "text": "A Service exposes a set of Pods as a network service. ClusterIP is the default type. Use LoadBalancer for external access.",
        "entities": [{"name": "Service", "type": "Resource"}, {"name": "Pod", "type": "Resource"}, {"name": "ClusterIP", "type": "Type"}, {"name": "LoadBalancer", "type": "Type"}],
        "relations": [{"source": "Service", "type": "EXPOSES", "target": "Pod"}, {"source": "Service", "type": "HAS_TYPE", "target": "ClusterIP"}]
    },
    "doc-3": {
        "id": "doc-3", "title": "Kubernetes ConfigMaps",
        "text": "A ConfigMap stores configuration data as key-value pairs. Pods can consume ConfigMaps as environment variables or mounted files.",
        "entities": [{"name": "ConfigMap", "type": "Resource"}, {"name": "Pod", "type": "Resource"}],
        "relations": [{"source": "ConfigMap", "type": "CONSUMED_BY", "target": "Pod"}]
    },
    "doc-4": {
        "id": "doc-4", "title": "Kubernetes Secrets",
        "text": "A Secret stores sensitive data like passwords and tokens. Use stringData for raw values. Secrets are mounted as files or env vars.",
        "entities": [{"name": "Secret", "type": "Resource"}, {"name": "Pod", "type": "Resource"}],
        "relations": [{"source": "Secret", "type": "MOUNTED_BY", "target": "Pod"}]
    },
    "doc-5": {
        "id": "doc-5", "title": "Scaling Deployments",
        "text": "To scale a Deployment, use kubectl scale deploy/NAME --replicas=N. The rolling update strategy ensures zero-downtime with maxUnavailable=0.",
        "entities": [{"name": "Deployment", "type": "Resource"}, {"name": "ReplicaSet", "type": "Resource"}],
        "relations": [{"source": "Deployment", "type": "USES", "target": "ReplicaSet"}, {"source": "ReplicaSet", "type": "ENSURES", "target": "zero-downtime"}]
    },
}

# Build simple in-memory graph
GRAPH_ENTITIES = {}
GRAPH_RELATIONS = []
for doc in DOCUMENTS.values():
    for ent in doc.get("entities", []):
        GRAPH_ENTITIES[ent["name"]] = ent
    for rel in doc.get("relations", []):
        GRAPH_RELATIONS.append(rel)

def graph_expand(entities: List[str], hops: int = 2) -> List[Dict]:
    """Simple graph expansion: find relations for given entities up to N hops."""
    results = []
    seen = set()
    current = set(entities)
    for hop in range(hops):
        next_entities = set()
        for rel in GRAPH_RELATIONS:
            if rel["source"] in current and rel["target"] not in seen:
                results.append({"source": rel["source"], "relation": rel["type"], "target": rel["target"], "hop": hop + 1})
                next_entities.add(rel["target"])
                seen.add(rel["target"])
            if rel["target"] in current and rel["source"] not in seen:
                results.append({"source": rel["source"], "relation": rel["type"], "target": rel["target"], "hop": hop + 1})
                next_entities.add(rel["source"])
                seen.add(rel["source"])
        current = next_entities
        if not current:
            break
    return results

class IngestRequest(BaseModel):
    documents: List[Dict[str, Any]]

class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True
    graph_hops: int = Field(default=2, ge=0, le=3)

class Source(BaseModel):
    doc_id: str
    title: str
    score: float
    snippet: str

class GraphPathItem(BaseModel):
    source: str
    relation: str
    target: str
    hop: int

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    graph_path: List[GraphPathItem]
    trace_id: str
    latency_ms: int

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str

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

# Set up tracing before startup, so every request gets a provider.
setup_tracing()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    trace_id, span_id = current_trace_ids()
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
    return response

@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok", app=settings.app_name, version=settings.version)

@app.post("/v1/graph-rag/ingest")
async def ingest(request: IngestRequest):
    with tracer.start_as_current_span("graphrag.ingest") as span:
        span.set_attribute("doc_count", len(request.documents))
        logger.info("ingest_request", extra={"doc_count": len(request.documents)})
        for doc in request.documents:
            logger.info("ingested_doc", extra={"doc_id": doc.get("id")})
        return {"status": "ok", "ingested": len(request.documents)}

@app.post("/v1/graph-rag/query", response_model=QueryResponse)
async def query(request: QueryRequest, response: Response):
    start = time.time()
    with tracer.start_as_current_span("graphrag.query") as span:
        # Use the span's own id, so the response and the trace agree.
        trace_id, _ = current_trace_ids()
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
        span.set_attribute("query", request.query)
        span.set_attribute("top_k", request.top_k)
        span.set_attribute("rerank", request.rerank)
        span.set_attribute("graph_hops", request.graph_hops)

        def retrieve(q: str, k: int):
            with tracer.start_as_current_span("retrieve") as s:
                q_lower = q.lower()
                results = []
                for doc_id, doc in DOCUMENTS.items():
                    score = 0
                    for word in q_lower.split():
                        if word in doc["text"].lower(): score += 1
                        if word in doc["title"].lower(): score += 2
                    if score > 0: results.append((doc_id, doc, score))
                results.sort(key=lambda x: x[2], reverse=True)
                return results[:k]

        def rerank(q: str, candidates: List):
            q_words = set(q.lower().split())
            for i, (doc_id, doc, score) in enumerate(candidates):
                title_words = set(doc["title"].lower().split())
                overlap = len(set(q.lower().split()) & title_words)
                candidates[i] = (doc_id, doc, score + overlap * 0.5)
            candidates.sort(key=lambda x: x[2], reverse=True)
            return candidates[:5]

        def generate(q: str, sources: List) -> str:
            snippets = [s[1]["text"][:200] for s in sources]
            return f"Based on the documentation: {' '.join(snippets[:2])}"

        def guardrail(answer: str) -> str:
            return answer

        retrieved = retrieve(request.query, request.top_k * 2)
        if request.rerank:
            retrieved = rerank(request.query, retrieved)

        # Expand the graph from the entities in the retrieved documents.
        graph_path = []
        if request.graph_hops > 0:
            # Extract entity names from retrieved docs
            query_entities = []
            for doc_id, doc, score in retrieved:
                for ent in doc.get("entities", []):
                    if ent["name"] not in query_entities:
                        query_entities.append(ent["name"])
            graph_path = graph_expand(query_entities, request.graph_hops)

        sources = [
            Source(doc_id=doc_id, title=doc["title"], score=round(score / 10.0, 2), snippet=doc["text"][:150] + "...")
            for doc_id, doc, score in retrieved[:request.top_k]
        ]

        answer = generate(request.query, retrieved)
        answer = guardrail(answer)
        latency = int((time.time() - start) * 1000)

        span.set_attribute("source_count", len(sources))
        span.set_attribute("latency_ms", latency)
        span.set_attribute("graph_path_len", len(graph_path))

        logger.info("query_completed", extra={
            "query": request.query, "sources": len(sources), "graph_path_len": len(graph_path),
            "latency_ms": latency, "trace_id": trace_id
        })

        return QueryResponse(
            answer=answer,
            sources=sources,
            graph_path=[GraphPathItem(**p) for p in graph_path],
            trace_id=trace_id,
            latency_ms=latency
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, log_config=None, access_log=False)