"""Configuration loading for the local Graph RAG application.

The private configuration lives outside the repository, normally at
~/.config/graphrag/config.yaml. Personal paths and database URLs must never be
committed. The repository only ships config.example.yaml.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(
    os.environ.get("GRAPHRAG_CONFIG", Path.home() / ".config" / "graphrag" / "config.yaml")
)

# Development DSNs from compose.yaml. Override them in the config file or env.
DEFAULT_EVAL_DSN = os.environ.get(
    "GRAPHRAG_EVAL_DSN",
    "postgresql://graphrag:graphrag-dev-only@localhost:5433/graphrag",
)
DEFAULT_PRIVATE_DSN = os.environ.get(
    "GRAPHRAG_PRIVATE_DSN",
    "postgresql://graphrag:graphrag-private-dev-only@localhost:5434/graphrag_private",
)

PUBLIC_CORPORA = {"lab"}
PRIVATE_CORPORA = {"notes", "papers"}


# A named source of documents (a folder of notes, or the papers project).
@dataclass
class SourceConfig:
    name: str
    kind: str
    path: Path
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    pdf_dir: str | None = None
    summaries_dir: str | None = None
    max_file_bytes: int = 20_000_000
    min_words: int = 15
    ocr: bool = False
    ocr_lang: str = "eng"
    ocr_min_words: int = 10
    ocr_dpi: int = 200

    # Build a source from its YAML mapping.
    @classmethod
    def from_mapping(cls, name: str, data: dict[str, Any]) -> "SourceConfig":
        return cls(
            name=name,
            kind=data.get("kind", "files"),
            path=Path(data["path"]).expanduser(),
            include=list(data.get("include", [])),
            exclude=list(data.get("exclude", [])),
            pdf_dir=data.get("pdf_dir"),
            summaries_dir=data.get("summaries_dir"),
            max_file_bytes=int(data.get("max_file_bytes", 20_000_000)),
            min_words=int(data.get("min_words", 15)),
            ocr=bool(data.get("ocr", False)),
            ocr_lang=str(data.get("ocr_lang", "eng")),
            ocr_min_words=int(data.get("ocr_min_words", 10)),
            ocr_dpi=int(data.get("ocr_dpi", 200)),
        )


# Runtime settings for models, databases and document sources.
@dataclass
class Settings:
    ollama_url: str = "http://localhost:11434"
    embed_model: str = "bge-m3-local"
    generate_model: str = "granite3.3-8b-local"
    fallback_model: str = "qwen3-8b-local"
    databases: dict[str, str] = field(
        default_factory=lambda: {"eval": DEFAULT_EVAL_DSN, "private": DEFAULT_PRIVATE_DSN}
    )
    sources: dict[str, SourceConfig] = field(default_factory=dict)
    chunk_words: int = 320
    chunk_overlap: int = 50
    vector_top_k: int = 30
    lexical_top_k: int = 30
    answer_top_k: int = 12
    graph_hops: int = 1
    rerank: bool = False
    rerank_candidates: int = 20
    rerank_model: str = ""
    require_graph: bool = False
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4318/v1/traces"
    otel_service_name: str = "graphrag-local"
    otel_console: bool = False

    # Return the DSN for a named database.
    def dsn(self, name: str) -> str:
        try:
            return self.databases[name]
        except KeyError as exc:
            raise SystemExit(f"unknown database {name!r}; use eval, private, or a DSN") from exc

    # Return a source by name, with a clear error when it is not configured.
    def source(self, name: str) -> SourceConfig:
        try:
            return self.sources[name]
        except KeyError as exc:
            raise SystemExit(
                f"source {name!r} is not configured; see config.example.yaml"
            ) from exc

    # Return every corpus name the application knows about.
    def corpora(self) -> list[str]:
        return sorted(PUBLIC_CORPORA | PRIVATE_CORPORA)


# Load settings from the private config file, falling back to local defaults.
def load_settings(path: Path | None = None) -> Settings:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise SystemExit(f"cannot read {config_path}: {exc}") from exc
    elif path is not None:
        raise SystemExit(f"config file not found: {config_path}")

    models = data.get("models", {}) or {}
    databases = dict(Settings().databases)
    databases.update(data.get("databases", {}) or {})
    sources = {
        name: SourceConfig.from_mapping(name, mapping)
        for name, mapping in (data.get("sources", {}) or {}).items()
    }
    otel = data.get("otel", {}) or {}
    return Settings(
        ollama_url=data.get("ollama_url", Settings.ollama_url),
        embed_model=models.get("embed", Settings.embed_model),
        generate_model=models.get("generate", Settings.generate_model),
        fallback_model=models.get("fallback", Settings.fallback_model),
        databases=databases,
        sources=sources,
        chunk_words=int(data.get("chunk_words", Settings.chunk_words)),
        chunk_overlap=int(data.get("chunk_overlap", Settings.chunk_overlap)),
        vector_top_k=int(data.get("vector_top_k", Settings.vector_top_k)),
        lexical_top_k=int(data.get("lexical_top_k", Settings.lexical_top_k)),
        answer_top_k=int(data.get("answer_top_k", Settings.answer_top_k)),
        graph_hops=int(data.get("graph_hops", Settings.graph_hops)),
        rerank=bool(data.get("rerank", Settings.rerank)),
        rerank_candidates=int(data.get("rerank_candidates", Settings.rerank_candidates)),
        rerank_model=str(data.get("rerank_model", Settings.rerank_model) or ""),
        require_graph=bool(data.get("require_graph", Settings.require_graph)),
        otel_enabled=bool(otel.get("enabled", Settings.otel_enabled)),
        otel_endpoint=str(otel.get("endpoint", Settings.otel_endpoint)),
        otel_service_name=str(otel.get("service_name", Settings.otel_service_name)),
        otel_console=bool(otel.get("console", Settings.otel_console)),
    )
