# Graph RAG Pattern — build, deploy, evaluate
#
# Usage:
#   make build          # build Docker image
#   make deploy         # apply k8s manifests
#   make eval           # run evaluation against deployed API
#   make port-forward   # port-forward for local testing
#   make clean          # remove k8s resources

.PHONY: build deploy eval port-forward clean test

IMAGE := boilerplate/graph-rag-api:1.0
NAMESPACE := k8s-lab
API_URL := http://localhost:8000

build:
	docker build -t $(IMAGE) mockup

deploy:
	kubectl apply -k k8s

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

# Run unit tests (if any)
test:
	@echo "No unit tests yet"

# Remove all resources
clean:
	kubectl delete -k k8s --ignore-not-found
	@echo "Cleaned up Graph RAG resources"

# Full cycle: build, deploy, eval, clean
full: build deploy eval clean