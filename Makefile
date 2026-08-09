include .env
export

PROJECT_NAME := loupe24k
SITE_NAME    ?= loupe24k.localhost
COMPOSE      := docker compose --project-name $(PROJECT_NAME) -f docker-compose.yml

.DEFAULT_GOAL := help

.PHONY: help build start stop restart logs shell bench setup-site install reset-site nuke seed test migrate

help:
	@echo ""
	@echo "  Loup 24K — ERPNext v15 Dev Environment"
	@echo "  ======================================="
	@echo ""
	@echo "  First-time setup:"
	@echo "    make install      Build image, start services, create site, seed data (all-in-one)"
	@echo "    --- or step by step ---"
	@echo "    make build        Build the custom Docker image"
	@echo "    make start        Start all services"
	@echo "    make setup-site   Create the ERPNext site and install apps"
	@echo "    make seed         Seed master/demo data"
	@echo ""
	@echo "  Daily use:"
	@echo "    make logs         Tail logs from all services"
	@echo "    make shell        Open a bash shell in the backend container"
	@echo "    make bench CMD=.. Run a bench command (e.g. make bench CMD='list-apps')"
	@echo "    make test         Run unit tests (no bench required)"
	@echo "    make seed         Seed master/demo data (idempotent, safe to re-run)"
	@echo "    make stop         Stop all services"
	@echo "    make restart      Restart all services"
	@echo ""
	@echo "  Danger zone:"
	@echo "    make reset-site   Drop and recreate the site (data loss!)"
	@echo "    make nuke         Remove containers AND volumes (total reset)"
	@echo ""

## ── Build ────────────────────────────────────────────────────────────────────

build:
	@echo ">>> Building custom ERPNext image with loupe24k app..."
	docker build --no-cache \
		--build-arg FRAPPE_BRANCH=$(FRAPPE_VERSION) \
		-t $(CUSTOM_IMAGE):$(CUSTOM_TAG) \
		.
	@echo ">>> Image built: $(CUSTOM_IMAGE):$(CUSTOM_TAG)"

## ── Lifecycle ────────────────────────────────────────────────────────────────

start:
	@echo ">>> Starting services..."
	$(COMPOSE) up -d

stop:
	$(COMPOSE) stop

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --tail=100

## ── Site setup ───────────────────────────────────────────────────────────────

# One-shot first-time setup: build image → start services → create site → seed data
install: build start setup-site seed
	@echo ""
	@echo "  ✓ Loupe 24K is ready."
	@echo "  Open: http://$(SITE_NAME):$(HTTP_PUBLISH_PORT)"
	@echo "  User: Administrator / $(ADMIN_PASSWORD)"
	@echo ""
	@echo "  Add to /etc/hosts if not present:"
	@echo "    127.0.0.1  $(SITE_NAME)"

setup-site:
	@echo ">>> Waiting for services to be ready..."
	@sleep 10
	@echo ">>> Creating site: $(SITE_NAME)"
	$(COMPOSE) exec backend bench new-site $(SITE_NAME) \
		--mariadb-user-host-login-scope='%' \
		--db-root-password $(DB_PASSWORD) \
		--admin-password $(ADMIN_PASSWORD) \
		--install-app erpnext \
		--install-app loupe24k
	@echo ">>> Enabling developer mode..."
	$(COMPOSE) exec backend bench --site $(SITE_NAME) set-config developer_mode 1
	$(COMPOSE) exec backend bench --site $(SITE_NAME) clear-cache
	@echo ">>> Setting default site..."
	$(COMPOSE) exec backend bench use $(SITE_NAME)
	@echo ""
	@echo ">>> Site ready! Open http://$(SITE_NAME):$(HTTP_PUBLISH_PORT)"
	@echo ">>> Username: Administrator"
	@echo ">>> Password: $(ADMIN_PASSWORD)"
	@echo ""
	@echo ">>> Add this to /etc/hosts if not already present:"
	@echo "    127.0.0.1  $(SITE_NAME)"

## ── Shell / bench shortcuts ──────────────────────────────────────────────────

shell:
	$(COMPOSE) exec backend bash

# Usage: make bench CMD="list-apps --site loupe24k.localhost"
bench:
	$(COMPOSE) exec backend bench $(CMD)

test:
	@echo ">>> Running unit tests..."
	cd apps/loupe24k && python3 -m pytest loupe24k/loupe_24k/doctype/ -v
	@echo ">>> Tests complete."

migrate:
	@echo ">>> Running bench migrate (loads workspace JSON, custom fields, patches)..."
	$(COMPOSE) exec backend bench --site $(SITE_NAME) migrate
	@echo ">>> Migrate complete."

seed:
	@echo ">>> Seeding master data..."
	$(COMPOSE) exec backend bench --site $(SITE_NAME) execute loupe24k.data.seed_data.seed
	@echo ">>> Seed complete."

## ── Danger zone ──────────────────────────────────────────────────────────────

reset-site:
	@echo ">>> WARNING: This will DROP the site database and recreate it."
	@read -p "Continue? [y/N] " yn; [ "$$yn" = "y" ] || exit 1
	$(COMPOSE) exec backend bench drop-site $(SITE_NAME) \
		--db-root-password $(DB_PASSWORD) --force || true
	$(MAKE) setup-site

nuke:
	@echo ">>> WARNING: This removes ALL containers and volumes (complete reset)."
	@read -p "Continue? [y/N] " yn; [ "$$yn" = "y" ] || exit 1
	$(COMPOSE) down -v --remove-orphans
