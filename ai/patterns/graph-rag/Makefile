# Graph RAG Pattern — build, deploy, evaluate
#
# Usage:
#   make build          # build Docker image
#   make deploy         # apply k8s manifests
#   make up             # build, deploy and wait for the rollout
#   make eval           # run evaluation against deployed API
#   make corpus-manifest# regenerate corpus/MANIFEST.json
#   make corpus-check   # validate the corpus and the golden set
#   make migrate        # apply the Postgres schema (idempotent)
#   make db-check       # prove idempotency and the hyperedge encoding
#   make app-test       # offline tests for the local application
#   make eval-local     # 42-question golden set against the local app
#   make port-forward   # port-forward for local testing
#   make clean          # remove k8s resources

.PHONY: build deploy up eval corpus-manifest corpus-check db-up migrate db-check \
  db-down db-shell private-db-up private-migrate private-db-shell private-db-down \
  venv app-test eval-local ingest-lab ingest-notes ingest-papers port-forward clean test

IMAGE := boilerplate/graph-rag-api:1.0
NAMESPACE := k8s-lab
API_URL := http://localhost:8000
DB_USER ?= graphrag
DB_NAME ?= graphrag
PRIVATE_DB_NAME ?= graphrag_private
PYTHON ?= .venv/bin/python

build:
	docker build -t $(IMAGE) mockup

deploy:
	kubectl apply -k k8s

# Build, deploy and wait for the rollout to finish
up: build deploy
	@echo "Waiting for rollout..."
	@kubectl rollout status deploy/graph-rag-api -n $(NAMESPACE) --timeout=180s

# Wait for rollout, then run eval against port-forwarded service
eval:
	@echo "Waiting for rollout..."
	@kubectl rollout status deploy/graph-rag-api -n $(NAMESPACE) --timeout=180s
	@echo "Starting port-forward..."
	@kubectl port-forward -n $(NAMESPACE) svc/graph-rag-api 8000:80 > /tmp/graph-rag-pf.log 2>&1 & \
	PF_PID=$$!; \
	sleep 5; \
	python3 eval/eval.py --url http://localhost:8000 --golden eval/golden_qa.jsonl; \
	kill $$PF_PID

port-forward:
	kubectl port-forward -n $(NAMESPACE) svc/graph-rag-api 8000:80

# Regenerate the corpus manifest after editing a document.
corpus-manifest:
	python3 corpus/tools/build_manifest.py

# Validate the corpus, its hashes, and the golden questions offline.
corpus-check:
	python3 corpus/tools/validate_corpus.py

# Start the local Postgres.
db-up:
	docker compose up -d postgres
	@printf 'waiting for postgres...\n'
	@until docker compose exec -T postgres pg_isready -U $(DB_USER) -d $(DB_NAME) >/dev/null 2>&1; do sleep 1; done

# Apply the schema; safe to run as often as wanted.
migrate: db-up
	docker compose exec -T -e PGOPTIONS='-c client_min_messages=warning' postgres \
	  psql -v ON_ERROR_STOP=1 -q -U $(DB_USER) -d $(DB_NAME) < db/schema.sql
	@printf 'schema applied\n'

# Prove the second migrate is a no-op and that hyperedges are stored correctly.
db-check:
	./db/check_schema.sh

# Stop and remove the local database (the named volume keeps the data).
db-down:
	docker compose down

# Open a psql session against the local database.
db-shell:
	docker compose exec postgres psql -U $(DB_USER) -d $(DB_NAME)

# Start the private notes/papers database on its own port and volume.
private-db-up:
	docker compose --profile private up -d postgres-private
	@printf 'waiting for the private postgres...\n'
	@until docker compose --profile private exec -T postgres-private \
	    pg_isready -U $(DB_USER) -d $(PRIVATE_DB_NAME) >/dev/null 2>&1; do sleep 1; done

# Apply the same schema to the private database.
private-migrate: private-db-up
	docker compose --profile private exec -T \
	  -e PGOPTIONS='-c client_min_messages=warning' postgres-private \
	  psql -v ON_ERROR_STOP=1 -q -U $(DB_USER) -d $(PRIVATE_DB_NAME) < db/schema.sql
	@printf 'private schema applied\n'

private-db-shell:
	docker compose --profile private exec postgres-private \
	  psql -U $(DB_USER) -d $(PRIVATE_DB_NAME)

# Stop the private database; its named volume keeps the index.
private-db-down:
	docker compose --profile private stop postgres-private

# Create the application virtualenv from app/requirements.txt.
venv:
	uv venv .venv
	uv pip install --python .venv/bin/python -r app/requirements.txt
	@printf 'venv ready: %s\n' "$(PYTHON)"

# Offline checks for the app: chunker, source loaders, stub pipeline.
app-test:
	$(PYTHON) -m unittest discover -s app/tests -v

# Score the local app against the 42-question golden set.
eval-local:
	$(PYTHON) eval/local_eval.py --json-out eval/local-results.json

# Rebuild the synthetic evaluation index with real local models.
ingest-lab:
	$(PYTHON) -m app.cli ingest lab --db eval

# Index the private notes and papers. Requires the private config file.
ingest-notes:
	$(PYTHON) -m app.cli ingest notes

ingest-papers:
	$(PYTHON) -m app.cli ingest papers

# Run the offline checks (the evaluation itself needs the service).
test: corpus-check
	python3 -m py_compile eval/eval.py corpus/tools/build_manifest.py corpus/tools/validate_corpus.py
	@echo "graph-rag offline checks pass"

# Remove all resources
clean:
	kubectl delete -k k8s --ignore-not-found
	@echo "Cleaned up Graph RAG resources"

# Full cycle: build, deploy, eval, clean
full: build deploy eval clean