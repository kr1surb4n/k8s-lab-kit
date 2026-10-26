"""Entity and relation extraction for the graph layer."""
from __future__ import annotations

import re
from typing import Any

from .llm import OllamaClient, OllamaError, parse_json_object

RELATION_RE = re.compile(r"[^A-Z0-9_]+")
MAX_ENTITY_LENGTH = 120
MAX_TEXT_CHARS = 3000
MAX_OUTPUT_TOKENS = 900

# Ollama enforces this schema, so the model cannot return truncated prose or
# malformed JSON when the output budget is large enough.
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                },
                "required": ["name", "type"],
            },
        },
        "relations": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "type": {"type": "string"},
                    "target": {"type": "string"},
                },
                "required": ["source", "type", "target"],
            },
        },
        "hyperedges": {
            "type": "array",
            "maxItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "relation": {"type": "string"},
                    "members": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 8,
                        "items": {"type": "string"},
                    },
                },
                "required": ["relation", "members"],
            },
        },
    },
    "required": ["entities", "relations", "hyperedges"],
}

SYSTEM_PROMPT = (
    "You extract a small knowledge graph from technical documents. "
    "Answer with one JSON object and nothing else."
)

PROMPT_TEMPLATE = """Extract the entities and relations that matter in this document.

Document title: {title}
Section: {section}

Return exactly this JSON shape:
{{
  "entities": [{{"name": "...", "type": "..."}}],
  "relations": [{{"source": "...", "type": "UPPER_SNAKE", "target": "..."}}],
  "hyperedges": [{{"relation": "UPPER_SNAKE", "members": ["...", "...", "..."]}}]
}}

Rules:
- 3 to 8 entities. Use names that appear in the text. Maximum 80 characters.
- Types are short nouns: Component, Resource, Exercise, Concept, Tool, Paper,
  Dataset, Method, Person, Organism.
- 2 to 8 relations. source and target must be entity names from this answer.
- Relation types are UPPER_SNAKE verbs, for example USES, PART_OF, OWNS,
  REQUIRES, CONNECTS_TO.
- At most one hyperedge, and only for a relation that genuinely involves three
  or more members at once. Omit the list when there is none. Never invent one.
- Keep the whole JSON answer under 700 tokens.
- No prose, no markdown, no comments outside the JSON.

Document text:
{text}
"""


# Normalize a relation type to upper snake case.
def relation_kind(value: str) -> str:
    cleaned = RELATION_RE.sub("_", str(value).upper()).strip("_")
    return (cleaned or "RELATED_TO")[:60]


# Trim an entity name and reject names that are too short or too long.
def clean_name(value: Any) -> str | None:
    name = re.sub(r"\s+", " ", str(value or "")).strip(" \t\n\"'`.,:;()[]{}")
    if len(name) < 2 or len(name) > MAX_ENTITY_LENGTH:
        return None
    return name


# Keep the first occurrence of each case-insensitive entity name.
def unique_entities(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for item in items:
        name = clean_name(item.get("name"))
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        node_type = re.sub(r"[^A-Za-z ]", "", str(item.get("type", "Entity"))).strip()
        result.append({"name": name, "type": node_type or "Entity"})
    return result


# Validate the model's JSON and return a safe graph fragment.
def normalize_extraction(data: dict) -> dict[str, Any]:
    entities = unique_entities(list(data.get("entities") or []))
    known = {entity["name"].lower(): entity["name"] for entity in entities}

    relations = []
    for item in list(data.get("relations") or []):
        source = clean_name(item.get("source"))
        target = clean_name(item.get("target"))
        if not source or not target or source.lower() == target.lower():
            continue
        for name in (source, target):
            if name.lower() not in known:
                known[name.lower()] = name
                entities.append({"name": name, "type": "Entity"})
        relations.append(
            {
                "source": known[source.lower()],
                "type": relation_kind(item.get("type", "RELATED_TO")),
                "target": known[target.lower()],
                "confidence": 0.8,
            }
        )

    hyperedges = []
    for item in list(data.get("hyperedges") or []):
        members = []
        for member in list(item.get("members") or []):
            name = clean_name(member)
            if not name:
                continue
            if name.lower() not in known:
                known[name.lower()] = name
                entities.append({"name": name, "type": "Entity"})
            members.append(known[name.lower()])
        members = list(dict.fromkeys(members))
        if len(members) < 3:
            continue
        hyperedges.append(
            {
                "relation": relation_kind(item.get("relation", "JOINTLY_RELATED")),
                "members": members,
                "confidence": 0.7,
            }
        )
    return {"entities": entities, "relations": relations, "hyperedges": hyperedges}


# Extract entities from Markdown emphasis and backticks for offline runs.
def stub_extract(document: Any) -> dict[str, Any]:
    bold = re.findall(r"\*\*([^*\n]{2,80})\*\*", document.text)
    code = re.findall(r"`([^`\n]{2,80})`", document.text)
    title_words = [word for word in re.findall(r"[A-Z][A-Za-z0-9-]{2,}", document.title)]
    names: list[str] = []
    for name in bold + code + title_words:
        cleaned = clean_name(name)
        if cleaned and cleaned.lower() not in {item.lower() for item in names}:
            names.append(cleaned)
    entities = [{"name": name, "type": "Concept"} for name in names[:15]]
    return {"entities": entities, "relations": [], "hyperedges": []}


# Build a graph from the paper's tags and summary metadata; no model call.
def tags_extract(document: Any) -> dict[str, Any]:
    raw_tags = [
        str(tag).strip().replace("\x00", "")
        for tag in (document.source.get("tags") or [])
        if str(tag).strip().replace("\x00", "")
    ]
    # A repeated tag would violate the edge member primary key.
    tags = list(dict.fromkeys(raw_tags))
    title = document.title
    entities = [{"name": title, "type": "Paper"}] + [
        {"name": tag, "type": "Topic"} for tag in tags
    ]
    relations = [
        {"source": title, "type": "HAS_TOPIC", "target": tag, "confidence": 1.0}
        for tag in tags
    ]
    # Several tags together describe the paper's scope, so they form a genuine
    # hyperedge rather than a chain of pairwise edges.
    hyperedges = []
    if len(tags) >= 3:
        hyperedges.append(
            {"relation": "COVERS_TOPICS", "members": tags, "confidence": 0.9}
        )
    return {"entities": entities, "relations": relations, "hyperedges": hyperedges}


# Run the chosen extractor over one document.
def extract_document(
    document: Any,
    mode: str = "llm",
    client: OllamaClient | None = None,
    model: str = "granite3.3-8b-local",
) -> dict[str, Any]:
    if mode == "none":
        return {"entities": [], "relations": [], "hyperedges": []}
    if mode == "stub":
        return stub_extract(document)
    if mode == "tags":
        return tags_extract(document)
    if client is None:
        raise ValueError("llm extraction needs an Ollama client")

    prompt = PROMPT_TEMPLATE.format(
        title=document.title,
        section=document.section,
        text=document.text[:MAX_TEXT_CHARS],
    )
    try:
        # A short context and output budget keeps per-document extraction
        # around ten seconds on the local GPU; long PDFs are represented by
        # their title, summary, and opening pages.
        text = client.chat(
            prompt,
            model,
            system=SYSTEM_PROMPT,
            temperature=0.0,
            num_predict=MAX_OUTPUT_TOKENS,
            num_ctx=4096,
            format_schema=EXTRACTION_SCHEMA,
        )
        try:
            data = parse_json_object(text)
        except ValueError:
            # A rare truncated answer gets one retry with a smaller prompt and
            # a larger output budget.
            retry = PROMPT_TEMPLATE.format(
                title=document.title,
                section=document.section,
                text=document.text[:2000],
            )
            text = client.chat(
                retry,
                model,
                system=SYSTEM_PROMPT,
                temperature=0.0,
                num_predict=900,
                num_ctx=4096,
                format_schema=EXTRACTION_SCHEMA,
            )
            data = parse_json_object(text)
    except (OllamaError, ValueError) as exc:
        raise RuntimeError(f"extraction failed for {document.id}: {exc}") from exc
    return normalize_extraction(data)
