HOMEPROJECT := $(CURDIR)
SYSTEM_IP := $(shell hostname -I | awk '{print $$1}')
COMPOSE := docker compose --env-file .env.docker

.PHONY: setup build start stop restart updater logs ps clean ip

setup:
	@test -f $(HOMEPROJECT)/.env.docker || cp $(HOMEPROJECT)/.env.docker.example $(HOMEPROJECT)/.env.docker
	@test -f $(HOMEPROJECT)/system.json || touch $(HOMEPROJECT)/system.json
	@echo "Creando directorios requeridos..."
	mkdir -p $(HOMEPROJECT)/data/logs
	mkdir -p $(HOMEPROJECT)/data/sources
	mkdir -p $(HOMEPROJECT)/data/tmp
	touch $(HOMEPROJECT)/data/sources/devices.csv
	@echo "Construyendo imágenes de docker..."
	$(COMPOSE) build
	@echo "Levantando aplicación..."
	$(COMPOSE) up -d
	@echo "Configuración finalizada. Revisa .env.docker si necesitas ajustar credenciales."

build:
	@echo "Construyendo imágenes de docker..."
	$(COMPOSE) build
	@echo "Levantando aplicación..."
	$(COMPOSE) up -d
	@echo "Aplicación levantada."

start:
	@echo "Levantando aplicación..."
	$(COMPOSE) up -d
	@echo "Aplicación levantada."

stop:
	@echo "Deteniendo aplicación..."
	$(COMPOSE) down
	@echo "Aplicación detenida."

restart: stop start

updater:
	$(COMPOSE) exec backend python -m icm updater

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

clean:
	@echo "Deteniendo aplicación y eliminando volúmenes (se pierden los datos de PostgreSQL)..."
	$(COMPOSE) down -v

ip:
	@echo $(SYSTEM_IP)
