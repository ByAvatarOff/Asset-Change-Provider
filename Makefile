.PHONY: all

SHELL=/bin/bash -e

.DEFAULT_GOAL := help

help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Local development commands
run-provider: ## Run provider service locally
	cd provider && uvicorn app.provide.main:app --host 0.0.0.0 --port 8000 --reload

run-aggregator: ## Run aggregator service locally
	cd aggregator && python main.py

# Docker commands
build: ## build all services
	docker-compose build

up: ## start all services in docker
	docker-compose up -d
	docker-compose ps

down: ## stop all services
	docker-compose down
