.PHONY: build-ui build-server build restart-ui restart-server restart logs-ui logs-server

# Rebuild images (required after code changes — restart alone won't recompile)
build-ui:
	docker compose up --build -d agent-ui

build-server:
	docker compose up --build -d agent-server

build: build-server build-ui

# Restart containers (use only for config/env changes, NOT code changes)
restart-ui:
	docker compose restart agent-ui

restart-server:
	docker compose restart agent-server

restart: restart-server restart-ui

# Logs
logs-ui:
	docker compose logs -f agent-ui

logs-server:
	docker compose logs -f agent-server
