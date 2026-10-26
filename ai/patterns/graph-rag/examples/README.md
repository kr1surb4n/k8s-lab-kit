# Graph RAG examples

Each file is a self-contained, runnable increment. They add to the same local
application and use the same eval database; none of them needs private notes.

| Example | What it demonstrates | Default |
|---|---|---|
| [Two-hop graph expansion](two-hop-graph-expansion.md) | Follow a shared entity from the retrieved documents into one other document | Off (`graph_hops: 1`) |
| [Local listwise reranker](reranker.md) | Reorder fused candidates with one local LLM call and fall back safely | Off (`rerank: false`) |
| [OCR for image-only PDFs](ocr-image-pdfs.md) | Render low-text PDF pages and read them with the `tesseract` CLI | Off (`ocr: false`) |
| [OpenTelemetry spans](opentelemetry-spans.md) | Trace answer/search with counts only, console or OTLP | Off (`otel.enabled: false`) |
| [Destructive failure drills](failure-drills.md) | Delete a cited document, empty `edge_nodes`; the answer must fail loudly | Guard off (`require_graph: false`) |
| [Kubernetes packaging](kubernetes-packaging.md) | Kustomize base with non-root, probes, resources, Secrets, NetworkPolicy | Rendered offline |

The main setup is in [`../app/README.md`](../app/README.md). Run commands from
`ai/patterns/graph-rag` unless a page says otherwise.
