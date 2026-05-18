from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule


PROJECT_DIR = "/opt/airflow/project"
VENV_DIR = f"{PROJECT_DIR}/.airflow_venv"
PYTHON_BIN = f"{VENV_DIR}/bin/python"

DEFAULT_ARGS = {
    "owner": "job-market",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def project_command(command: str) -> str:
    return f"cd {PROJECT_DIR} && {command}"


with DAG(
    dag_id="job_market_batch_pipeline",
    description="Collecte, charge, transforme et entraîne les données Job Market.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["job-market", "batch", "dbt", "ml"],
) as dag:
    install_project_dependencies = BashOperator(
        task_id="install_project_dependencies",
        bash_command=project_command(
            f"python -m venv {VENV_DIR} && "
            f"{PYTHON_BIN} -m pip install --upgrade pip && "
            f"{PYTHON_BIN} -m pip install -r requirements.txt"
        ),
    )
    install_project_dependencies.as_setup()

    collect_france_travail = BashOperator(
        task_id="collect_france_travail",
        bash_command=project_command(f"{PYTHON_BIN} src/data/make_dataset.py --source france_travail"),
    )

    collect_welcome_to_the_jungle = BashOperator(
        task_id="collect_welcome_to_the_jungle",
        bash_command=project_command(f"{PYTHON_BIN} src/data/make_dataset.py --source welcome"),
    )

    load_raw_to_postgres = BashOperator(
        task_id="load_raw_to_postgres",
        bash_command=project_command(f"{PYTHON_BIN} src/data/normalizers/load_raw_to_postgres.py --source all"),
        trigger_rule=TriggerRule.ALL_DONE,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=project_command(f"{PYTHON_BIN} scripts/run_dbt.py run"),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=project_command(f"{PYTHON_BIN} scripts/run_dbt.py test"),
    )

    train_ml_models = BashOperator(
        task_id="train_ml_models",
        bash_command=project_command(
            f"{PYTHON_BIN} -m src.models.train_models --model-dir models --n-neighbors ${{ML_NEIGHBORS:-50}}"
        ),
    )

    install_project_dependencies >> [collect_france_travail, collect_welcome_to_the_jungle]
    [collect_france_travail, collect_welcome_to_the_jungle] >> load_raw_to_postgres
    load_raw_to_postgres >> dbt_run >> dbt_test >> train_ml_models
