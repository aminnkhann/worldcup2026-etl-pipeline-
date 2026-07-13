from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


class FakeDAG:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.tasks = []


class FakePythonOperator:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        kwargs["dag"].tasks.append(self)


def _load_dag_module(monkeypatch):
    airflow = types.ModuleType("airflow")
    airflow.DAG = FakeDAG
    operators = types.ModuleType("airflow.operators")
    python_operator = types.ModuleType("airflow.operators.python")
    python_operator.PythonOperator = FakePythonOperator

    monkeypatch.setitem(sys.modules, "airflow", airflow)
    monkeypatch.setitem(sys.modules, "airflow.operators", operators)
    monkeypatch.setitem(sys.modules, "airflow.operators.python", python_operator)

    dag_path = Path(__file__).parents[1] / "airflow" / "dags" / "worldcup_pipeline.py"
    spec = importlib.util.spec_from_file_location("worldcup_airflow_dag", dag_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_airflow_dags_schedule_non_overlapping_sync_modes(monkeypatch):
    module = _load_dag_module(monkeypatch)

    facts_dag = module.worldcup_facts_sync
    full_dag = module.worldcup_full_sync

    assert facts_dag.kwargs["schedule"] == "0 6 * * 1-6"
    assert full_dag.kwargs["schedule"] == "0 6 * * 0"
    assert facts_dag.kwargs["catchup"] is False
    assert full_dag.kwargs["max_active_runs"] == 1
    assert facts_dag.tasks[0].kwargs["op_kwargs"] == {"facts_only": True}
    assert full_dag.tasks[0].kwargs["op_kwargs"] == {"facts_only": False}
    assert facts_dag.tasks[0].kwargs["python_callable"] is module.run
