from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import ShortCircuitOperator
from airflow.utils.trigger_rule import TriggerRule


PIPELINE_CONTAINER = "job_market_pipeline"
DOCKER_SERVICES = "job_market_postgres job_market_pipeline"

DEFAULT_ARGS = {
    "owner": "job-market",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def pipeline_command(command: str) -> str:
    return f"docker exec {PIPELINE_CONTAINER} {command}"


def has_loaded_rows(**context) -> bool:
    task_instance = context["ti"]
    load_task_ids = [
        "load_raw_france_travail",
        "load_raw_welcome_to_the_jungle",
    ]
    inserted_rows = [
        int(task_instance.xcom_pull(task_ids=task_id) or 0)
        for task_id in load_task_ids
    ]
    total_inserted = sum(inserted_rows)
    print(f"Inserted rows by source: {dict(zip(load_task_ids, inserted_rows))}")
    print(f"Total inserted rows before dbt: {total_inserted}")
    return total_inserted > 0


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
    start_docker_services = BashOperator(
        task_id="start_docker_services",
        bash_command=f"docker start {DOCKER_SERVICES}",
    )
    start_docker_services.as_setup()

    collect_france_travail = BashOperator(
        task_id="collect_france_travail",
        bash_command=pipeline_command("python src/data/make_dataset.py --source francetravail --update"),
    )

    collect_welcome_to_the_jungle = BashOperator(
        task_id="collect_welcome_to_the_jungle",
        bash_command=pipeline_command("python src/data/make_dataset.py --source welcometothejungle --update"),
    )

    load_raw_france_travail = BashOperator(
        task_id="load_raw_france_travail",
        bash_command=pipeline_command(
            "python src/data/normalizers/load_raw_to_postgres.py --source francetravail --xcom-inserted-rows"
        ),
        do_xcom_push=True,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    load_raw_welcome_to_the_jungle = BashOperator(
        task_id="load_raw_welcome_to_the_jungle",
        bash_command=pipeline_command(
            "python src/data/normalizers/load_raw_to_postgres.py --source welcometothejungle --xcom-inserted-rows"
        ),
        do_xcom_push=True,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    should_run_dbt = ShortCircuitOperator(
        task_id="should_run_dbt",
        python_callable=has_loaded_rows,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=pipeline_command("python scripts/run_dbt.py run"),
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=pipeline_command("python scripts/run_dbt.py test"),
    )

    train_ml_models = BashOperator(
        task_id="train_ml_models",
        bash_command=pipeline_command(
            "python -m src.models.train_models --model-dir models"
        ),
    )

    start_docker_services >> [collect_france_travail, collect_welcome_to_the_jungle]
    collect_france_travail >> load_raw_france_travail
    collect_welcome_to_the_jungle >> load_raw_welcome_to_the_jungle
    [load_raw_france_travail, load_raw_welcome_to_the_jungle] >> should_run_dbt >> dbt_run
    dbt_run >> dbt_test >> train_ml_models
