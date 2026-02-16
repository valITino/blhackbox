.PHONY: help build up down logs shell test lint format clean reset-graph wordlists

COMPOSE := docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

build: ## Build all containers
	NEO4J_PASSWORD=build-placeholder $(COMPOSE) build

up: ## Start all services
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

logs-blhackbox: ## Tail blhackbox logs
	$(COMPOSE) logs -f blhackbox

logs-hexstrike: ## Tail hexstrike logs
	$(COMPOSE) logs -f hexstrike

shell: ## Open a shell in the blhackbox container
	$(COMPOSE) exec blhackbox bash

test: ## Run tests
	$(COMPOSE) exec blhackbox pytest tests/ -v --tb=short

test-local: ## Run tests locally (outside Docker)
	pytest tests/ -v --tb=short

lint: ## Run linter
	ruff check blhackbox/ tests/

format: ## Auto-format code
	ruff format blhackbox/ tests/

clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info

reset-graph: ## Reset the Neo4j knowledge graph
	$(COMPOSE) exec blhackbox python -m scripts.reset_graph

wordlists: ## Download common wordlists
	mkdir -p wordlists
	@echo "Downloading common wordlists..."
	curl -sL -o wordlists/common.txt \
		https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt
	curl -sL -o wordlists/subdomains-top1million-5000.txt \
		https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt
	curl -sL -o wordlists/raft-medium-directories.txt \
		https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-medium-directories.txt
	@echo "Done. Wordlists saved to ./wordlists/"

recon: ## Quick recon example (requires TARGET env var)
	$(COMPOSE) exec blhackbox blhackbox recon --target $(TARGET) --authorized

report: ## Generate report for a session (requires SESSION env var)
	$(COMPOSE) exec blhackbox blhackbox report --session $(SESSION) --format pdf
