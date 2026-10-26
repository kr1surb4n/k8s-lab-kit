# Graph RAG Pattern — build, deploy, evaluate
#
# Usage:
#   make build          # build Docker image
#   make deploy         # apply k8s manifests
#   make up             # build, deploy and wait for the rollout
#   make eval           # run evaluation against deployed API
#   make corpus-manifest# regenerate corpus/MANIFEST.json
#   make corpus-check   # validate the corpus and the golden set
#   make port-forward   # port-forward for local testing
#   make clean          # remove k8s resources

.PHONY: build deploy up eval corpus-manifest corpus-check port-forward clean test

IMAGE := boilerplate/graph-rag-api:1.0
NAMESPACE := k8s-lab
API_URL := http://localhost:8000

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