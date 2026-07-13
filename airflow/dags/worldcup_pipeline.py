"""Scheduled orchestration for the World Cup ETL pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from worldcup_pipeline.run import run

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def build_sync_dag(*, dag_id: str, schedule: str, facts_only: bool, description: str) -> DAG:
    dag = DAG(
        dag_id=dag_id,
        description=description,
        schedule=schedule,
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        catchup=False,
        max_active_runs=1,
        default_args=DEFAULT_ARGS,
        tags=["world-cup", "etl", "postgresql"],
    )

    PythonOperator(
        task_id="run_pipeline",
        python_callable=run,
        op_kwargs={"facts_only": facts_only},
        execution_timeout=timedelta(hours=3),
        dag=dag,
    )
    return dag


worldcup_facts_sync = build_sync_dag(
    dag_id="worldcup_facts_sync",
    schedule="0 6 * * 1-6",
    facts_only=True,
    description="Refresh matches, standings, and scorers Monday through Saturday.",
)

worldcup_full_sync = build_sync_dag(
    dag_id="worldcup_full_sync",
    schedule="0 6 * * 0",
    facts_only=False,
    description="Refresh dimensions and facts every Sunday.",
)
