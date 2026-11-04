"""MLflow model entry point: construct the agent when the model is loaded."""

from mlflow.models import ModelConfig, set_model

from arxiv_curator.agent import ArxivAgent

set_model(ArxivAgent(**ModelConfig().to_dict()))
