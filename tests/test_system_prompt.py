from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from arxiv_curator.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("env", ["dev", "acc", "prd"])
def test_prompt_is_loaded_relative_to_config_file(env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(str(ROOT / "project_config.yml"), env)
    assert cfg.system_prompt == (ROOT / "prompts/linkedin_content.txt").read_text().strip()
    assert "150-250 words" in cfg.system_prompt


def test_agent_sends_configured_prompt_before_history_and_request():
    from arxiv_curator.agent import ArxivAgent

    cfg = load_config(str(ROOT / "project_config.yml"))
    agent = ArxivAgent.__new__(ArxivAgent)
    agent.system_prompt = cfg.system_prompt
    agent.llm_endpoint = cfg.llm_endpoint
    agent.memory = None
    agent._tools_dict = {}
    agent.model_serving_client = MagicMock()
    agent.model_serving_client.responses.create.return_value = SimpleNamespace(
        output=[], output_text="Generated post", id="response-1"
    )
    history = [{"role": "user", "content": "My previous topic was reasoning."}]
    request = [{"role": "user", "content": "Write a follow-up LinkedIn post."}]

    with patch("arxiv_curator.agent.mlflow.update_current_trace"):
        ArxivAgent.call_and_run_tools.__wrapped__(
            agent, request_input=request, previous_messages=history
        )

    sent = agent.model_serving_client.responses.create.call_args.kwargs["input"]
    assert sent[:3] == [{"role": "system", "content": cfg.system_prompt}] + history + request
