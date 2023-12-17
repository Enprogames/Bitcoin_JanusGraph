# Makefile Configuration
DOCKER_COMPOSE_FILE := docker-compose.yml
DOCKER_COMPOSE := docker-compose -f $(DOCKER_COMPOSE_FILE)
MAIN_CONTAINER := app

# Docker Compose Commands
DOCKER_COMPOSE_EXEC_APP := $(DOCKER_COMPOSE) exec $(MAIN_CONTAINER)
DOCKER_COMPOSE_RUN := $(DOCKER_COMPOSE) run --rm
DOCKER_COMPOSE_UP := $(DOCKER_COMPOSE) up -d
DOCKER_COMPOSE_DOWN := $(DOCKER_COMPOSE) down
DOCKER_COMPOSE_BUILD := $(DOCKER_COMPOSE) build
DOCKER_COMPOSE_PS := $(DOCKER_COMPOSE) ps
DOCKER_COMPOSE_STOP := $(DOCKER_COMPOSE) stop
DOCKER_COMPOSE_START := $(DOCKER_COMPOSE) start
DOCKER_COMPOSE_RESTART := $(DOCKER_COMPOSE) restart

# Populate Parameters (default values)
BLOCK_HEIGHT ?= 100
API_ENDPOINT ?= "https://blockchain.info/rawblock/"

# Targets
.PHONY: all run populate populate_blocks populate_graph test clean full_clean

all: populate

run:
	@echo "Running app..."
	@$(DOCKER_COMPOSE_UP)

populate: populate_blocks populate_graph

populate_blocks:
	@echo "Populating blocks up to height $(BLOCK_HEIGHT) and API endpoint $(API_ENDPOINT)..."
	@$(DOCKER_COMPOSE_EXEC_APP) bash -c "python src/populate_blockchain.py $(BLOCK_HEIGHT) --endpoint $(API_ENDPOINT)"

delete_blocks:
	@echo "Deleting blocks..."
	@$(DOCKER_COMPOSE_EXEC_APP) bash -c "python src/populate_blockchain.py --delete"

populate_graph:
	@echo "Populating graph..."
	@$(DOCKER_COMPOSE_EXEC_APP) bash -c "python src/graph_populate.py"

test:
	@echo "Running tests..."
	@$(DOCKER_COMPOSE_EXEC_APP) bash -c "pytest"

clean:
	@echo "Cleaning up..."
	@$(DOCKER_COMPOSE_DOWN)

full_clean:
	@echo "Performing full cleanup..."
	@$(DOCKER_COMPOSE_DOWN) -v --rmi all --remove-orphans