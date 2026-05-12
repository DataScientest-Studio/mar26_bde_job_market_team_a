PYTHON := .venv/Scripts/python.exe
PIP := $(PYTHON) -m pip
DBT := $(PYTHON) scripts/run_dbt.py
DBT_SELECT ?=
LOADER := src/data/normalizers/load_raw_to_postgres.py
COLLECTOR := src/data/make_dataset.py
API_HOST := 127.0.0.1
API_PORT := 8000

.PHONY: help install api api-stop api-docker-build api-docker-up api-docker-down api-docker-logs collect-france-travail collect-welcome postgres-up postgres-down postgres-reset load-raw load-raw-all reset-db_with_new_data dbt-run dbt-test pipeline

help:
	@echo Available targets:
	@echo   install
	@echo   api
	@echo   api-stop
	@echo   api-docker-build
	@echo   api-docker-up
	@echo   api-docker-down
	@echo   api-docker-logs
	@echo   collect-france-travail
	@echo   collect-welcome
	@echo   postgres-up
	@echo   postgres-down
	@echo   postgres-reset
	@echo   load-raw
	@echo   load-raw-all
	@echo   reset-db_with_new_data
	@echo   dbt-run
	@echo   dbt-test
	@echo   pipeline

install:
	$(PIP) install -r requirements.txt

api:
	$(PYTHON) -m uvicorn src.api.main:app --host $(API_HOST) --port $(API_PORT) --reload

api-docker-build:
	docker compose build api

api-docker-up:
	docker compose up -d api

api-docker-down:
	docker compose stop api

api-docker-logs:
	docker compose logs -f api

collect-france-travail:
	$(PYTHON) $(COLLECTOR) --source france_travail

collect-welcome:
	$(PYTHON) $(COLLECTOR) --source welcome

postgres-up:
	docker compose up -d postgres

postgres-down:
	docker compose down

postgres-reset:
	docker compose down -v
	docker compose up -d postgres

load-raw:
	$(PYTHON) $(LOADER) --source all

load-raw-all:
	$(PYTHON) $(LOADER) --source all --all-files

reset-db-and-load:
	$(PYTHON) $(LOADER) --source all --all-files --reset-landing

reset-db_with_new_data: reset-db-and-load dbt-run

dbt-run:
	$(DBT) run $(if $(DBT_SELECT),--select $(DBT_SELECT),)

dbt-test:
	$(DBT) test $(if $(DBT_SELECT),--select $(DBT_SELECT),)

pipeline: collect-france-travail collect-welcome load-raw dbt-run dbt-test
