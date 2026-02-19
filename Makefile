.PHONY: help up up-full down logs test test-local lint format clean \
       status portainer gateway-logs ollama-pull ollama-shell \
       neo4j-browser logs-ollama-mcp logs-kali logs-hexstrike \
       logs-agent-ingestion logs-agent-processing logs-agent-synthesis \
       restart-ollama-mcp restart-kali restart-hexstrike restart-agents \
       push-all wordlists recon report

COMPOSE := docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-26s\033[0m %s\n", $$1, $$2}'

# ── Core ───────────────────────────────────────────────────────
up: ## Start core stack (9 containers)
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) --profile neo4j down

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

# ── Stack management ───────────────────────────────────────────
up-full: ## Start full stack including Neo4j (10 containers)
	$(COMPOSE) --profile neo4j up -d

# ── Testing & Code Quality ─────────────────────────────────────
test: ## Run tests locally
	pytest tests/ -v --tb=short

test-local: ## Run tests locally (alias)
	pytest tests/ -v --tb=short

lint: ## Run linter
	ruff check blhackbox/ tests/

format: ## Auto-format code
	ruff format blhackbox/ tests/

clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) --profile neo4j down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info

# ── Ollama ──────────────────────────────────────────────────────
ollama-pull: ## Pull default Ollama model into container
	docker exec blhackbox-ollama ollama pull $$(grep OLLAMA_MODEL .env | cut -d= -f2)

ollama-shell: ## Shell into Ollama container
	docker exec -it blhackbox-ollama /bin/bash

# ── Monitoring ──────────────────────────────────────────────────
portainer: ## Open Portainer dashboard
	@open https://localhost:9443 2>/dev/null || xdg-open https://localhost:9443

gateway-logs: ## Live MCP tool call log (every Claude tool invocation)
	$(COMPOSE) logs -f mcp-gateway

logs-ollama-mcp: ## Tail Ollama MCP server logs
	$(COMPOSE) logs -f ollama-mcp

logs-kali: ## Tail Kali MCP server logs
	$(COMPOSE) logs -f kali-mcp

logs-hexstrike: ## Tail HexStrike logs
	$(COMPOSE) logs -f hexstrike

logs-agent-ingestion: ## Tail Ingestion Agent logs
	$(COMPOSE) logs -f agent-ingestion

logs-agent-processing: ## Tail Processing Agent logs
	$(COMPOSE) logs -f agent-processing

logs-agent-synthesis: ## Tail Synthesis Agent logs
	$(COMPOSE) logs -f agent-synthesis

status: ## Health status of all containers
	$(COMPOSE) ps

neo4j-browser: ## Open Neo4j Browser
	@open http://localhost:7474 2>/dev/null || xdg-open http://localhost:7474

# ── Per-service restart ──────────────────────────────────────────
restart-ollama-mcp: ## Restart Ollama MCP server
	$(COMPOSE) restart ollama-mcp

restart-kali: ## Restart Kali MCP server
	$(COMPOSE) restart kali-mcp

restart-hexstrike: ## Restart HexStrike MCP server
	$(COMPOSE) restart hexstrike

restart-agents: ## Restart all 3 agent containers
	$(COMPOSE) restart agent-ingestion agent-processing agent-synthesis

# ── Recon & Reporting ──────────────────────────────────────────
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
	blhackbox recon --target $(TARGET) --authorized

report: ## Generate report for a session (requires SESSION env var)
	blhackbox report --session $(SESSION) --format pdf

# ── Build and push (Docker Hub: crhacky/blhackbox) ──────────────
push-all: ## Build and push all custom images to Docker Hub
	docker build -f docker/kali-mcp.Dockerfile -t crhacky/blhackbox:kali-mcp .
	docker build -f docker/hexstrike.Dockerfile -t crhacky/blhackbox:hexstrike .
	docker build -f docker/ollama-mcp.Dockerfile -t crhacky/blhackbox:ollama-mcp .
	docker build -f docker/agent-ingestion.Dockerfile -t crhacky/blhackbox:agent-ingestion .
	docker build -f docker/agent-processing.Dockerfile -t crhacky/blhackbox:agent-processing .
	docker build -f docker/agent-synthesis.Dockerfile -t crhacky/blhackbox:agent-synthesis .
	docker push crhacky/blhackbox:kali-mcp
	docker push crhacky/blhackbox:hexstrike
	docker push crhacky/blhackbox:ollama-mcp
	docker push crhacky/blhackbox:agent-ingestion
	docker push crhacky/blhackbox:agent-processing
	docker push crhacky/blhackbox:agent-synthesis
