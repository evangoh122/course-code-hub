"""Test the tracing notebook's experiment setup without running its LLM examples."""

import os
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from databricks.sdk.service.catalog import TableType
from mlflow.entities.trace_location import UnityCatalog

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks/4.0.uc_traces_setup.py"
SETUP = NOTEBOOK.read_text()


@pytest.fixture
def tracing():
    with ExitStack() as stack:
        tracing = SimpleNamespace()
        stack.enter_context(patch.dict(os.environ, {}, clear=False))
        tracing.cfg = SimpleNamespace(
            experiment_name="/Shared/llmops-course",
            catalog="catalog",
            schema="schema",
            warehouse_id="warehouse",
        )
        stack.enter_context(patch("arxiv_curator.config.load_config", return_value=tracing.cfg))
        stack.enter_context(patch("arxiv_curator.config.get_env", return_value="dev"))
        session = stack.enter_context(patch("pyspark.sql.SparkSession"))
        tracing.spark = session.builder.getOrCreate.return_value
        tracing.tracking = stack.enter_context(patch("mlflow.set_tracking_uri"))
        tracing.workspace = stack.enter_context(
            patch("databricks.sdk.WorkspaceClient")
        ).return_value
        tracing.table_names = [
            "llmops_otel_" + name for name in ("annotations", "logs", "metrics", "spans")
        ]
        tracing.view_names = ["llmops_trace_metadata", "llmops_trace_unified"]
        tracing.workspace.tables.list.return_value = (
            [
                SimpleNamespace(name=name, table_type=TableType.MANAGED)
                for name in tracing.table_names
            ]
            + [SimpleNamespace(name=name, table_type=TableType.VIEW) for name in tracing.view_names]
            + [SimpleNamespace(name="arxiv_papers", table_type=TableType.MANAGED)]
        )
        tracing.dbutils = MagicMock()
        tracing.dbutils.secrets.get.return_value = "sp-id"
        tracing.get_experiment = stack.enter_context(patch("mlflow.get_experiment_by_name"))
        tracing.set_experiment = stack.enter_context(patch("mlflow.set_experiment"))
        tracing.location = UnityCatalog("catalog", "schema", "llmops")
        tracing.experiment = SimpleNamespace(
            experiment_id="123", name=tracing.cfg.experiment_name, trace_location=tracing.location
        )
        tracing.set_experiment.return_value = tracing.experiment
        yield tracing


def test_missing_experiment_is_created_with_uc_storage(tracing):
    tracing.get_experiment.return_value = None
    exec(compile(SETUP, str(NOTEBOOK), "exec"), {"dbutils": tracing.dbutils})
    tracing.get_experiment.assert_called_once_with(tracing.cfg.experiment_name)
    assert_grants(tracing)
    kwargs = tracing.set_experiment.call_args.kwargs
    assert kwargs["experiment_name"] == tracing.cfg.experiment_name
    assert kwargs["trace_location"].table_prefix == "llmops"
    assert kwargs["trace_location"].catalog_name == "catalog"
    assert kwargs["trace_location"].schema_name == "schema"
    assert os.environ["MLFLOW_TRACING_SQL_WAREHOUSE_ID"] == "warehouse"


def test_existing_experiment_is_selected_without_creation(tracing):
    tracing.get_experiment.return_value = tracing.experiment
    exec(compile(SETUP, str(NOTEBOOK), "exec"), {"dbutils": tracing.dbutils})
    tracing.set_experiment.assert_called_once_with(experiment_id="123")
    assert_grants(tracing)


@pytest.mark.parametrize("location", (None, UnityCatalog("different", "schema", "llmops")))
def test_incompatible_existing_trace_storage_is_not_changed(tracing, location):
    tracing.experiment.trace_location = location
    tracing.get_experiment.return_value = tracing.experiment
    with pytest.raises(ValueError, match="different trace location"):
        exec(compile(SETUP, str(NOTEBOOK), "exec"), {"dbutils": tracing.dbutils})
    tracing.set_experiment.assert_not_called()


def assert_grants(tracing):
    statements = [call.args[0] for call in tracing.spark.sql.call_args_list]
    assert len(statements) == 6
    for name in tracing.table_names:
        assert f"GRANT SELECT, MODIFY ON TABLE catalog.schema.`{name}` TO `sp-id`" in statements
    for name in tracing.view_names:
        assert f"GRANT SELECT ON TABLE catalog.schema.`{name}` TO `sp-id`" in statements
    tracing.tracking.assert_not_called()
    tracing.dbutils.secrets.get.assert_called_once_with(
        catalog="catalog", schema="schema", key="databricks_client_id"
    )


def test_experiment_is_set_before_grants(tracing):
    tracing.get_experiment.return_value = tracing.experiment
    tracing.spark.sql.side_effect = lambda statement: tracing.set_experiment.assert_called_once()
    exec(compile(SETUP, str(NOTEBOOK), "exec"), {"dbutils": tracing.dbutils})
    assert_grants(tracing)
