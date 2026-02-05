import asyncio
import pytest

from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot
from autobyteus.memory.working_context_snapshot_serializer import WorkingContextSnapshotSerializer
from autobyteus.memory.store.working_context_snapshot_store import WorkingContextSnapshotStore


class DummyLLM(BaseLLM):
    async def _send_messages_to_llm(self, _messages, **_kwargs):
        return CompleteResponse(content="ok")

    async def _stream_messages_to_llm(self, _messages, **_kwargs):
        yield ChunkResponse(content="ok", is_complete=True)


@pytest.mark.asyncio
async def test_restore_agent_flow_bootstrap_loads_working_context_snapshot(tmp_path):
    # Reset factory singleton for test isolation
    if hasattr(AgentFactory, '_instance'):
        AgentFactory._instance = None

    agent_id = "agent_restore"
    snapshot = WorkingContextSnapshot()
    snapshot.append_message(Message(role=MessageRole.SYSTEM, content="System"))
    snapshot.append_message(Message(role=MessageRole.USER, content="Hello"))

    payload = WorkingContextSnapshotSerializer.serialize(
        snapshot,
        {"schema_version": 1, "agent_id": agent_id},
    )
    working_context_snapshot_store = WorkingContextSnapshotStore(base_dir=tmp_path, agent_id=agent_id)
    working_context_snapshot_store.write(agent_id, payload)

    model = LLMModel(
        name="dummy",
        value="dummy",
        canonical_name="dummy",
        provider=LLMProvider.OPENAI,
        llm_class=DummyLLM,
        runtime=LLMRuntime.API,
    )
    llm = DummyLLM(model, LLMConfig())

    config = AgentConfig(
        name="RestoreAgent",
        role="tester",
        description="restore flow",
        llm_instance=llm,
        tools=[],
    )

    factory = AgentFactory()
    agent = factory.restore_agent(agent_id=agent_id, config=config, memory_dir=str(tmp_path))
    agent.start()

    # Wait for bootstrap to finish
    for _ in range(50):
        if agent.context.current_status == AgentStatus.IDLE:
            break
        await asyncio.sleep(0.05)

    assert agent.context.current_status == AgentStatus.IDLE
    messages = agent.context.state.memory_manager.get_working_context_messages()
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]
    assert messages[1].content == "Hello"

    await agent.stop()
