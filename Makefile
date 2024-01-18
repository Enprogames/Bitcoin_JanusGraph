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

EXEC_APP := $(DOCKER_COMPOSE_EXEC_APP) bash -c

# Populate Parameters (default values)
BLOCK_HEIGHT ?= 100000
API_ENDPOINT ?= "https://blockchain.info/rawblock/"

# Alembic Parameters
MESSAGE ?= "Alembic migration"

# Targets
.PHONY: all start stop ps populate populate_blocks populate_graph test clean full_clean

all: populate

start:
	@echo "Starting containers..."
	@$(DOCKER_COMPOSE_UP) || (echo "Failed to start containers" && exit 1)

ps:
	@echo "Listing containers..."
	@$(DOCKER_COMPOSE_PS)

stop:
	@echo "Stopping containers..."
	@$(DOCKER_COMPOSE_STOP)

populate: start populate_blocks populate_graph

populate_blockchain:
	@$(EXEC_APP) "\
		python src/blockchain_populate.py\
		--height $(BLOCK_HEIGHT)\
		--endpoint $(API_ENDPOINT)"

delete_blockchain:
	@$(EXEC_APP) "python src/blockchain_populate.py --delete"

migrate:
	@$(EXEC_APP) "alembic revision --autogenerate -m '$(MESSAGE)'"

populate_graph:
	@$(EXEC_APP) "python src/graph_populate.py"

delete_graph:
	@$(EXEC_APP) "python src/graph_populate.py --delete"

test:
	@$(EXEC_APP) "pytest"

clean:
	@echo "Cleaning up..."
	@$(DOCKER_COMPOSE_DOWN)

full_clean:
	@echo "This will remove all containers, images, and volumes."
	@read -p "Are you sure? [y/N]: " confirm && [ $$confirm == y ] || exit 1
	@$(DOCKER_COMPOSE_DOWN) -v --rmi all --remove-orphans
