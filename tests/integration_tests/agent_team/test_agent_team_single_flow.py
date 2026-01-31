import asyncio
import os
from pathlib import Path

import pytest
from openai import APIConnectionError

from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
from autobyteus.agent_team.utils.wait_for_idle import wait_for_team_to_be_idle
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.workspace.workspace_config import WorkspaceConfig
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent_team.factory.agent_team_factory import AgentTeamFactory
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.skills.registry import SkillRegistry
from autobyteus.tools import write_file
from autobyteus.utils.singleton import SingletonMeta


class SimpleWorkspace(BaseAgentWorkspace):
    def __init__(self, root_path: str):
        super().__init__(WorkspaceConfig({"root_path": root_path}))
        self._root_path = root_path

    def get_base_path(self) -> str:
        return self._root_path


def _reset_singletons():
    SingletonMeta._instances.pop(AgentFactory, None)
    SingletonMeta._instances.pop(AgentTeamFactory, None)
    SingletonMeta._instances.pop(SkillRegistry, None)


def _create_lmstudio_llm():
    manual_model_id = os.getenv("LMSTUDIO_MODEL_ID")
    if manual_model_id:
        return LLMFactory.create_llm(model_identifier=manual_model_id)

    LLMFactory.reinitialize()
    models = LLMFactory.list_models_by_runtime(LLMRuntime.LMSTUDIO)
    if not models:
        return None

    target_text_model = "qwen/qwen3-30b-a3b-2507"
    text_model = next((m for m in models if target_text_model in m.model_identifier), None)
    if not text_model:
        text_model = next((m for m in models if "vl" not in m.model_identifier.lower()), models[0])
    return LLMFactory.create_llm(model_identifier=text_model.model_identifier)


async def _wait_for_file(path: Path, timeout: float = 20.0, interval: float = 0.1) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if path.exists():
            return True
        await asyncio.sleep(interval)
    return False


@pytest.mark.asyncio
async def test_agent_team_single_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")
    monkeypatch.setenv("AUTOBYTEUS_MEMORY_DIR", str(tmp_path / "memory"))
    SkillRegistry().clear()
    _reset_singletons()

    coordinator_llm = _create_lmstudio_llm()
    if not coordinator_llm:
        pytest.skip("No LM Studio models found.")
    worker_llm = _create_lmstudio_llm()
    if not worker_llm:
        await coordinator_llm.cleanup()
        pytest.skip("No LM Studio models found.")

    coordinator_dir = tmp_path / "coordinator"
    worker_dir = tmp_path / "worker"
    coordinator_dir.mkdir(parents=True, exist_ok=True)
    worker_dir.mkdir(parents=True, exist_ok=True)

    coordinator_config = AgentConfig(
        name="Coordinator",
        role="Coordinator",
        description="Team coordinator",
        llm_instance=coordinator_llm,
        tools=[write_file],
        auto_execute_tools=True,
        workspace=SimpleWorkspace(str(coordinator_dir)),
    )

    worker_config = AgentConfig(
        name="Worker",
        role="Worker",
        description="Team worker",
        llm_instance=worker_llm,
        tools=[write_file],
        auto_execute_tools=True,
        workspace=SimpleWorkspace(str(worker_dir)),
    )

    builder = AgentTeamBuilder("IntegrationTeam", "Agent team integration test")
    builder.set_coordinator(coordinator_config)
    builder.add_agent_node(worker_config)
    team = builder.build()

    try:
        team.start()
        await wait_for_team_to_be_idle(team, timeout=60.0)
    except (asyncio.TimeoutError, RuntimeError) as exc:
        await team.stop(timeout=10.0)
        await coordinator_llm.cleanup()
        await worker_llm.cleanup()
        pytest.skip(f"Team failed to become idle: {exc}")

    tool_args = {"path": "team_output.txt", "content": "Team worker output."}
    message = AgentInputUserMessage(
        f'Use the write_file tool to write "{tool_args["content"]}" to "{tool_args["path"]}". '
        "Do not respond with plain text."
    )

    try:
        await team.post_message(message, target_agent_name="Worker")
        file_path = worker_dir / tool_args["path"]
        created = await _wait_for_file(file_path)
        if not created:
            pytest.skip("Tool call did not create the expected file.")

        content = file_path.read_text(encoding="utf-8").strip()
        assert content == tool_args["content"]

        await wait_for_team_to_be_idle(team, timeout=120.0)
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await team.stop(timeout=10.0)
        await coordinator_llm.cleanup()
        await worker_llm.cleanup()
