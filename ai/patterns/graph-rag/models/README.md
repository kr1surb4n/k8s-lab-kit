# Local Ollama models for Graph RAG

Phase 17 runs embeddings and generation on the host through Ollama. The
cluster service is a thin client: models are never baked into the image.

The model set was chosen and imported on 2026-10-26 with Ollama 0.30.7. The
GGUF files are already in `~/Downloads`; no download is needed.

## Required

| Role | Ollama model | Source GGUF | Size | Notes |
|---|---|---|---|---|
| Embeddings | `bge-m3-local` | `~/Downloads/bge-m3-q8_0.gguf` | 606 MB | 1024-dim, 8192 ctx, multilingual; `/api/embed` verified |
| Generation | `granite3.3-8b-local` | `~/Downloads/granite-3.3-8b-instruct-Q4_K_M.gguf` | 4.7 GB | 8.2B, Q4_K_M, 128k native ctx; RAG-focused |

## Optional

| Role | Ollama model | Source GGUF | Size | Notes |
|---|---|---|---|---|
| Fallback generator | `qwen3-8b-local` | `~/Downloads/Qwen3-8B-Q4_K_M.gguf` | 4.7 GB | Add `/no_think`; chat verified |
| Fast fallback | `phi-4-mini-local` | `~/Downloads/Phi-4-mini-instruct-Q4_K_M.gguf` | 2.4 GB | Not imported; use if latency matters |
| Structured extraction | `nuextract-local` | `~/Downloads/NuExtract-v1.5-Q4_K_M.gguf` | 2.3 GB | Not imported; only if Granite JSON extraction is weak |

`nomic-embed-text-v1.5.Q8_0.gguf` (140 MB, 768-dim) is a smaller embedding
fallback. It is not used by default because `bge-m3` has the better
multilingual coverage and 1024-dim vectors.

## Reranking

Ollama has no rerank endpoint. Start with a listwise LLM rerank using
`granite3.3-8b-local`; this needs no extra model. If the evaluation shows that a
cross-encoder is needed, use `BAAI/bge-reranker-v2-m3` through
`FlagEmbedding` or `sentence-transformers` outside Ollama (about 2.3 GB). Do not
add it before the first real evaluation.

## GPU note

The host has an 8 GB RTX 5070 Laptop GPU. A `llama.cpp` server may hold about
6.4 GiB (PID 47489 at the time of writing), leaving about 1.7 GiB free. The 8B
models fall back to CPU while it runs. Stop that server only if you own it, then
check `nvidia-smi`. With the GPU free, Granite or Qwen3 Q4_K_M plus an 8k context
should fit in about 6.5 GB.

## Import

Run from this directory. The `FROM` paths are for this workstation; replace them
on another machine.

```bash
ollama create bge-m3-local -f bge-m3.Modelfile
ollama create granite3.3-8b-local -f granite3.3-8b.Modelfile
ollama create qwen3-8b-local -f qwen3-8b.Modelfile   # optional
```

The GGUFs did not carry chat templates, so the Granite and Qwen3 Modelfiles add
them explicitly. The Qwen3 template needs `/no_think` in the prompt to avoid the
default thinking block.

## Verify

```bash
# 1024-dimensional embeddings
curl -s http://localhost:11434/api/embed \
  -d '{"model":"bge-m3-local","input":["hello"]}' \
  | jq '.embeddings[0] | length'

# Primary generator; expected: ok
curl -s http://localhost:11434/api/chat \
  -d '{"model":"granite3.3-8b-local","messages":[{"role":"user","content":"Reply with exactly: ok"}],"stream":false}' \
  | jq -r '.message.content'

# Fallback generator; expected: ok
curl -s http://localhost:11434/api/chat \
  -d '{"model":"qwen3-8b-local","messages":[{"role":"user","content":"Reply with exactly: ok /no_think"}],"stream":false}' \
  | jq -r '.message.content'
```

The imported models live in the system Ollama store at
`/usr/share/ollama/.ollama/models`, not `~/.ollama` (which is only 108K on this
host).
