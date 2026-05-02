.PHONY: help train run backend frontend up down build logs mlflow grafana clean test backtest

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN  = \033[0;32m
YELLOW = \033[0;33m
CYAN   = \033[0;36m
RESET  = \033[0m

help:
	@echo "$(CYAN)FX AlphaLab — MLOps Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)Development$(RESET)"
	@echo "  make backend        Start backend locally"
	@echo "  make frontend       Start frontend locally"
	@echo "  make run            Run one signal cycle"
	@echo ""
	@echo "$(YELLOW)Training$(RESET)"
	@echo "  make train          Train all agents (v3)"
	@echo "  make train-unified  Train on unified matrix (10 years)"
	@echo "  make backtest       Run backtest on signals.csv"
	@echo ""
	@echo "$(YELLOW)Docker$(RESET)"
	@echo "  make up             Start all services"
	@echo "  make down           Stop all services"
	@echo "  make build          Build all Docker images"
	@echo "  make logs           Show backend logs"
	@echo "  make train-docker   Run training in Docker"
	@echo ""
	@echo "$(YELLOW)Monitoring$(RESET)"
	@echo "  make mlflow         Open MLflow UI"
	@echo "  make grafana        Open Grafana UI"
	@echo ""
	@echo "$(YELLOW)Utils$(RESET)"
	@echo "  make clean          Remove __pycache__ and .pyc files"
	@echo "  make test           Run tests"

# ── Local Development ─────────────────────────────────────────────────────────

backend:
	@echo "$(GREEN)Starting backend...$(RESET)"
	cd Deployment/Backend && python main.py

frontend:
	@echo "$(GREEN)Starting frontend...$(RESET)"
	cd Deployment/Frontend/my-app && npm run dev

run:
	@echo "$(GREEN)Running one signal cycle...$(RESET)"
	cd fx_alphalab && python run_agent.py --once

run-loop:
	@echo "$(GREEN)Running agent loop (60 min cycles)...$(RESET)"
	cd fx_alphalab && python run_agent.py

# ── Training ──────────────────────────────────────────────────────────────────

train:
	@echo "$(GREEN)Training all agents (v3)...$(RESET)"
	cd fx_alphalab && python train_agents_v3.py

train-unified:
	@echo "$(GREEN)Training on unified matrix (10 years)...$(RESET)"
	cd fx_alphalab && python scripts/train_agents_v3_unified.py

backtest:
	@echo "$(GREEN)Running backtest...$(RESET)"
	cd fx_alphalab && python scripts/backtest.py

# ── Docker ───────────────────────────────────────────────────────────────────

up:
	@echo "$(GREEN)Starting all services...$(RESET)"
	

	docker-compose -f docker-compose.yml up -d
	@echo ""
	@echo "$(CYAN)Services running:$(RESET)"
	@echo "  Frontend  → http://localhost:3000"
	@echo "  Backend   → http://localhost:8080"
	@echo "  MLflow    → http://localhost:5000"
	@echo "  Grafana   → http://localhost:3001"

down:
	@echo "$(YELLOW)Stopping all services...$(RESET)"
	docker-compose -f docker-compose.yml down

build:
	@echo "$(GREEN)Building Docker images...$(RESET)"
	docker-compose -f docker-compose.yml build

logs:
	docker-compose -f docker-compose.yml logs -f backend

logs-all:
	docker-compose -f docker-compose.yml logs -f

train-docker:
	@echo "$(GREEN)Running training in Docker...$(RESET)"
	docker-compose -f docker-compose.yml --profile training up training

# ── Monitoring ────────────────────────────────────────────────────────────────

mlflow:
	@echo "$(CYAN)MLflow UI: http://localhost:5000$(RESET)"
	docker-compose -f docker-compose.yml up -d mlflow

grafana:
	@echo "$(CYAN)Grafana UI: http://localhost:3001$(RESET)"
	@echo "$(CYAN)Login: admin / alphalab123$(RESET)"
	docker-compose -f docker-compose.yml up -d grafana prometheus

# ── Utils ─────────────────────────────────────────────────────────────────────

clean:
	@echo "$(YELLOW)Cleaning cache files...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true

test:
	@echo "$(GREEN)Running tests...$(RESET)"
	cd fx_alphalab && python -m pytest tests/ -v 2>/dev/null || python test.py

status:
	@echo "$(CYAN)Service Status:$(RESET)"
	docker-compose -f docker-compose.yml ps
