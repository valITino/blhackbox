.PHONY: help build up up-direct down logs shell test lint format clean \
       reset-graph wordlists recon report \
       build-all status portainer gateway-logs ollama-pull ollama-shell \
       neo4j-browser logs-blhackbox logs-hexstrike logs-aggregator \
       logs-kali restart-aggregator restart-kali test-local

COMPOSE := docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Core ───────────────────────────────────────────────────────

build: ## Build blhackbox CLI image
	NEO4J_PASSWORD=build-placeholder $(COMPOSE) build blhackbox

build-all: ## Build ALL service images (including MCP servers)
	NEO4J_PASSWORD=build-placeholder $(COMPOSE) build blhackbox
	NEO4J_PASSWORD=build-placeholder $(COMPOSE) --profile direct build

up: ## Start infrastructure + MCP Gateway + Portainer
	$(COMPOSE) up -d

up-direct: ## Start everything with MCP servers in compose (no Gateway)
	$(COMPOSE) --profile direct up -d

down: ## Stop all services
	$(COMPOSE) --profile direct down

logs: ## Tail logs from all services
	$(COMPOSE) --profile direct logs -f

shell: ## Open a shell in the blhackbox CLI container
	$(COMPOSE) exec blhackbox bash

test: ## Run tests in Docker
	$(COMPOSE) exec blhackbox pytest tests/ -v --tb=short

test-local: ## Run tests locally (outside Docker)
	pytest tests/ -v --tb=short

lint: ## Run linter
	ruff check blhackbox/ tests/

format: ## Auto-format code
	ruff format blhackbox/ tests/

clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) --profile direct down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info

# ── Infrastructure ─────────────────────────────────────────────

status: ## Show health status of all containers
	$(COMPOSE) --profile direct ps

portainer: ## Open Portainer CE dashboard in browser
	@echo "Portainer CE → https://localhost:9443"
	@open https://localhost:9443 2>/dev/null || xdg-open https://localhost:9443 2>/dev/null || echo "Open https://localhost:9443 manually"

gateway-logs: ## Tail MCP Gateway logs (shows Claude tool calls)
	$(COMPOSE) logs -f mcp-gateway

neo4j-browser: ## Open Neo4j Browser
	@open http://localhost:7474 2>/dev/null || xdg-open http://localhost:7474 2>/dev/null || echo "Open http://localhost:7474 manually"

ollama-pull: ## Pull the default Ollama model into the container
	docker exec blhackbox-ollama ollama pull $$(grep '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo llama3.3)

ollama-shell: ## Open a shell in the Ollama container
	docker exec -it blhackbox-ollama /bin/bash

# ── Service Logs ───────────────────────────────────────────────

logs-blhackbox: ## Tail blhackbox CLI logs
	$(COMPOSE) logs -f blhackbox

logs-hexstrike: ## Tail HexStrike logs
	$(COMPOSE) --profile direct logs -f hexstrike

logs-aggregator: ## Tail aggregator MCP server logs
	$(COMPOSE) --profile direct logs -f aggregator

logs-kali: ## Tail Kali MCP server logs
	$(COMPOSE) --profile direct logs -f kali-mcp

# ── Service Management ────────────────────────────────────────

restart-aggregator: ## Restart aggregator without full stack restart
	$(COMPOSE) --profile direct restart aggregator

restart-kali: ## Restart Kali MCP server
	$(COMPOSE) --profile direct restart kali-mcp

# ── Recon & Reporting ──────────────────────────────────────────

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
