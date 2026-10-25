# RAG Pattern — build, deploy, evaluate
#
# Usage:
#   make build          # build Docker image
#   make deploy         # apply k8s manifests
#   make eval           # run evaluation against deployed API
#   make port-forward   # port-forward for local testing
#   make clean          # remove k8s resources

.PHONY: build deploy eval port-forward clean test

IMAGE := boilerplate/rag-api:1.0
NAMESPACE := k8s-lab
API_URL := http://localhost:8000

build:
	docker build -t $(IMAGE) ../mockup

deploy:
	kubectl apply -k .

# Wait for rollout, then run eval against port-forwarded service
eval:
	@echo "Waiting for rollout..."
	@kubectl rollout status deploy/rag-api -n $(NAMESPACE) --timeout=120s
	@echo "Starting port-forward..."
	@kubectl port-forward -n $(NAMESPACE) svc/rag-api 8000:80 > /tmp/rag-pf.log 2>&1 & \
	PF_PID=$$!; \
	sleep 5; \
	python3 eval/eval.py --url http://localhost:8000 --golden eval/golden_qa.jsonl; \
	kill $$PF_PID

port-forward:
	kubectl port-forward -n $(NAMESPACE) svc/rag-api 8000:80

# Run unit tests (if any)
test:
	@echo "No unit tests yet"

# Remove all resources
clean:
	kubectl delete -k . --ignore-not-found
	@echo "Cleaned up RAG resources"

# Full cycle: build, deploy, eval, clean
full: build deploy eval clean