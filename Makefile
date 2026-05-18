PYTHON := .venv/Scripts/python.exe
PIP := $(PYTHON) -m pip
DBT := $(PYTHON) scripts/run_dbt.py
DBT_SELECT ?=
LOADER := src/data/normalizers/load_raw_to_postgres.py
COLLECTOR := src/data/make_dataset.py
API_HOST := 127.0.0.1
API_PORT := 8000
DASHBOARD_PORT := 8501
MODEL_DIR := models
ML_NEIGHBORS := 50

.PHONY: help install api api-stop api-docker-build api-docker-up api-docker-down api-docker-logs dashboard dashboard-docker-up dashboard-docker-down dashboard-docker-logs airflow ml-train ml-check collect-france-travail collect-welcome postgres-up postgres-down postgres-reset load-raw load-raw-all reset-db_with_new_data dbt-run dbt-test pipeline

help:
	@echo Available targets:
	@echo.
	@echo App:
	@echo   install
	@echo   api
	@echo   api-stop
	@echo   api-docker-build
	@echo   api-docker-up
	@echo   api-docker-down
	@echo   api-docker-logs
	@echo   dashboard
	@echo   dashboard-docker-up
	@echo   dashboard-docker-down
	@echo   dashboard-docker-logs
	@echo   airflow
	@echo.
	@echo ML:
	@echo   ml-train          Train ML models from PostgreSQL and write artifacts
	@echo   ml-check          Compile code and train ML models
	@echo.
	@echo Data pipeline:
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

dashboard:
	$(PYTHON) -m streamlit run src/dashboard/streamlit_app.py --server.port $(DASHBOARD_PORT)

dashboard-docker-up:
	docker compose up -d dashboard

dashboard-docker-down:
	docker compose stop dashboard

dashboard-docker-logs:
	docker compose logs -f dashboard

airflow:
	@if not exist airflow\.env copy airflow\.env.example airflow\.env
	docker compose up -d --build postgres airflow-postgres airflow-init airflow-webserver airflow-scheduler

ml-train:
	$(PYTHON) -m src.models.train_models --model-dir $(MODEL_DIR) --n-neighbors $(ML_NEIGHBORS)

ml-check:
	$(PYTHON) -m compileall src
	$(MAKE) ml-train

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
