.PHONY: help up up-full up-gateway down logs test test-local lint format clean nuke \
       pull status health portainer gateway-logs ollama-pull ollama-shell \
       claude-code \
       neo4j-browser logs-ollama-mcp logs-kali logs-hexstrike \
       logs-agent-ingestion logs-agent-processing logs-agent-synthesis \
       restart-ollama-mcp restart-kali restart-hexstrike restart-agents \
       push-all wordlists recon report

COMPOSE := docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-26s\033[0m %s\n", $$1, $$2}'

# ── Core ───────────────────────────────────────────────────────
pull: ## Pull all pre-built images from Docker Hub
	$(COMPOSE) pull

up: ## Start core stack (8 containers — no gateway)
	$(COMPOSE) up -d

down: ## Stop all services (all profiles)
	$(COMPOSE) --profile gateway --profile neo4j --profile claude-code down

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

# ── Stack variations ─────────────────────────────────────────────
up-full: ## Start full stack: core + Neo4j (9 containers)
	$(COMPOSE) --profile neo4j up -d

up-gateway: ## Start core + MCP Gateway for Claude Desktop / ChatGPT (9 containers)
	$(COMPOSE) --profile gateway up -d

# ── Testing & Code Quality ─────────────────────────────────────
test: ## Run tests locally
	pytest tests/ -v --tb=short

test-local: ## Run tests locally (alias)
	pytest tests/ -v --tb=short

lint: ## Run linter
	ruff check blhackbox/ tests/

format: ## Auto-format code
	ruff format blhackbox/ tests/

clean: ## Remove containers, volumes, networks, and build artifacts (keeps images)
	$(COMPOSE) --profile gateway --profile neo4j --profile claude-code down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info

nuke: ## Full cleanup: containers + volumes + ALL images (frees max disk space)
	@echo "\033[1;33m  WARNING: This will remove ALL blhackbox containers, volumes, AND images.\033[0m"
	@echo "\033[2m  You will need to 'docker compose pull' or 'docker compose build' again.\033[0m"
	@echo ""
	$(COMPOSE) --profile gateway --profile neo4j --profile claude-code down -v --remove-orphans --rmi all
	@echo ""
	@echo "\033[2m  Pruning dangling images and build cache...\033[0m"
	docker image prune -f
	docker builder prune -f
	@echo ""
	@echo "\033[2m  Removing downloaded Ollama models (if volume still exists)...\033[0m"
	docker volume rm blhackbox_ollama_models 2>/dev/null || true
	docker volume rm blhackbox_portainer_data 2>/dev/null || true
	docker volume rm blhackbox_neo4j_data 2>/dev/null || true
	docker volume rm blhackbox_neo4j_logs 2>/dev/null || true
	docker volume rm blhackbox_results 2>/dev/null || true
	docker volume rm blhackbox_wordlists 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info
	@echo ""
	@echo "\033[32m  Done. Run 'docker system df' to verify disk usage.\033[0m"

# ── Claude Code (Docker) ────────────────────────────────────────
claude-code: ## Build and launch Claude Code in a Docker container
	$(COMPOSE) --profile claude-code pull claude-code || $(COMPOSE) --profile claude-code build claude-code
	$(COMPOSE) --profile claude-code run --rm claude-code

# ── Health & Status ──────────────────────────────────────────────
status: ## Health status of all containers
	@echo ""
	@echo "\033[1m  blhackbox Container Status\033[0m"
	@echo "\033[2m  ──────────────────────────────────────\033[0m"
	@$(COMPOSE) --profile gateway --profile neo4j --profile claude-code ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $(COMPOSE) ps
	@echo ""

health: ## Quick health check of all MCP servers
	@echo ""
	@echo "\033[1m  MCP Server Health Check\033[0m"
	@echo "\033[2m  ──────────────────────────────────────\033[0m"
	@printf "  %-22s " "Kali MCP (9001)"; \
		docker exec blhackbox-kali-mcp python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9001/sse')" > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "HexStrike (8888)"; \
		curl -sf --max-time 3 http://localhost:8888/health > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "Ollama MCP (9000)"; \
		docker exec blhackbox-ollama-mcp python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/sse')" > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "Ollama (11434)"; \
		docker exec blhackbox-ollama ollama list > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "Agent Ingestion"; \
		docker exec blhackbox-agent-ingestion python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "Agent Processing"; \
		docker exec blhackbox-agent-processing python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "Agent Synthesis"; \
		docker exec blhackbox-agent-synthesis python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[31m[FAIL]\033[0m"
	@printf "  %-22s " "MCP Gateway (8080)"; \
		curl -sf --max-time 3 http://localhost:8080/mcp > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m" || echo "\033[33m[OFF]\033[0m  (optional — enable with: make up-gateway)"
	@printf "  %-22s " "Portainer (9443)"; \
		curl -skf --max-time 3 https://localhost:9443 > /dev/null 2>&1 \
		&& echo "\033[32m[OK]\033[0m  https://localhost:9443" || echo "\033[31m[FAIL]\033[0m"
	@echo ""

# ── Ollama ──────────────────────────────────────────────────────
ollama-pull: ## Pull default Ollama model into container
	docker exec blhackbox-ollama ollama pull $$(grep OLLAMA_MODEL .env | cut -d= -f2)

ollama-shell: ## Shell into Ollama container
	docker exec -it blhackbox-ollama /bin/bash

# ── Monitoring ──────────────────────────────────────────────────
portainer: ## Open Portainer dashboard (first run: create admin account)
	@echo ""
	@echo "\033[1m  Portainer Web UI\033[0m"
	@echo "\033[2m  ──────────────────────────────────────\033[0m"
	@echo "  URL:  \033[36mhttps://localhost:9443\033[0m"
	@echo ""
	@echo "  First run: Create an admin account within 5 minutes of startup."
	@echo "  If the window expired, restart: docker compose restart portainer"
	@echo ""
	@open https://localhost:9443 2>/dev/null || xdg-open https://localhost:9443 2>/dev/null || echo "  Open the URL above in your browser."

gateway-logs: ## Live MCP tool call log (requires --profile gateway)
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
	docker build -f docker/claude-code.Dockerfile -t crhacky/blhackbox:claude-code .
	docker push crhacky/blhackbox:kali-mcp
	docker push crhacky/blhackbox:hexstrike
	docker push crhacky/blhackbox:ollama-mcp
	docker push crhacky/blhackbox:agent-ingestion
	docker push crhacky/blhackbox:agent-processing
	docker push crhacky/blhackbox:agent-synthesis
	docker push crhacky/blhackbox:claude-code
