.PHONY: help clean build deploy test local kind aws docs

# Default target
help:
	@echo "Distributed Key-Value Database - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make install     Install Python dependencies"
	@echo "  make clean       Clean Python cache and logs"
	@echo "  make test        Run all demos and tests"
	@echo ""
	@echo "Local Deployment:"
	@echo "  make local       Start local cluster"
	@echo "  make local-test  Start local cluster and run tests"
	@echo ""
	@echo "Kubernetes Deployment:"
@echo "  make kind        Deploy to Kind cluster"
@echo "  make kind-test   Deploy to Kind and run tests"
@echo "  make cleanup     Clean up all resources"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        Generate documentation"
	@echo ""

# Development
install:
	pip install -r requirements.txt

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f node*.log 2>/dev/null || true
	rm -rf data/ 2>/dev/null || true

test:
	python demo/cluster_demo_runner_local.py --all

# Local deployment
local:
	./scripts/start-cluster-local.sh

local-test: local
	sleep 10
	python demo/cluster_demo_runner_local.py vector_clock_db --config config/config.yaml

# Kind deployment
kind:
	./scripts/build-and-deploy.sh full

kind-test: kind
	sleep 30
	kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py vector_clock_db --config demo/config.yaml --use-existing



# Cleanup
cleanup:
	./scripts/build-and-deploy.sh delete-kind
	kind delete cluster --name kvdb-cluster 2>/dev/null || true
	docker system prune -af

# Documentation
docs:
	@echo "Documentation is available in the docs/ directory"
	@echo "Available guides:"
	@ls docs/*.md | sed 's/docs\//  - /' | sed 's/\.md//' 