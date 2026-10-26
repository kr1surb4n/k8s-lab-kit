"""Optional OpenTelemetry tracing for retrieval and answer spans.

Tracing is off by default. When enabled it exports to the console and/or an
OTLP/HTTP endpoint. Span attributes are counts and settings only; question text
and passage text never leave the process in a span.
"""
from __future__ import annotations

import atexit
import json
import logging
import sys
from contextlib import contextmanager
from typing import Any, Iterator

LOGGER = logging.getLogger("graphrag.telemetry")

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - requirements install the optional stack
    trace = None
    OTLPSpanExporter = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None
    SimpleSpanProcessor = None
    OTEL_AVAILABLE = False

_TRACER = None
_PROVIDER = None
_CONFIG_KEY: tuple[Any, ...] | None = None


# Return whether the application configured an active tracer.
def enabled() -> bool:
    return _TRACER is not None


# Format an exported span as one JSON line for the console exporter.
def _one_line_span(exported_span) -> str:
    data = json.loads(exported_span.to_json())
    return json.dumps(data, separators=(",", ":")) + "\n"


# Build a tracer from settings, or leave tracing disabled.
def configure_telemetry(settings, exporter=None, force: bool = False):
    global _TRACER, _PROVIDER, _CONFIG_KEY
    key = (
        bool(settings.otel_enabled),
        settings.otel_endpoint,
        settings.otel_service_name,
        bool(settings.otel_console),
        id(exporter),
    )
    if _CONFIG_KEY == key and not force:
        return _TRACER
    # A caller with no exporter may reuse a tracer that was configured by a
    # test or by the service startup with an explicit exporter.
    if (
        exporter is None
        and _TRACER is not None
        and _CONFIG_KEY is not None
        and _CONFIG_KEY[:4] == key[:4]
    ):
        return _TRACER
    if force:
        shutdown()
    _CONFIG_KEY = key
    if not settings.otel_enabled:
        _TRACER = None
        return None
    if not OTEL_AVAILABLE:
        LOGGER.warning("OpenTelemetry is enabled but the SDK is not installed")
        _TRACER = None
        return None

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    if exporter is None:
        if settings.otel_console:
            provider.add_span_processor(
                SimpleSpanProcessor(
                    ConsoleSpanExporter(out=sys.stderr, formatter=_one_line_span)
                )
            )
        if settings.otel_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint))
            )
    else:
        # Tests pass an in-memory exporter and expect spans immediately.
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    _PROVIDER = provider
    _TRACER = provider.get_tracer("graphrag")
    atexit.register(shutdown)
    return _TRACER


# Close the provider so buffered spans are flushed.
def shutdown() -> None:
    global _TRACER, _PROVIDER
    if _PROVIDER is not None:
        try:
            _PROVIDER.shutdown()
        except Exception:  # noqa: BLE001 - shutdown must not mask the program result
            LOGGER.debug("telemetry shutdown failed", exc_info=True)
    _TRACER = None
    _PROVIDER = None


# Start a span when enabled; yield None when tracing is off.
@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    if _TRACER is None:
        yield None
        return
    with _TRACER.start_as_current_span(name, attributes=attributes) as current:
        yield current


# Return the current trace id as 32 hex characters, or an empty string.
def current_trace_id() -> str:
    if not OTEL_AVAILABLE:
        return ""
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return ""
    return format(context.trace_id, "032x")
