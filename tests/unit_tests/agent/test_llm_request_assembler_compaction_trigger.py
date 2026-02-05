import time

import pytest

from autobyteus.agent.llm_request_assembler import LLMRequestAssembler
from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.messages import MessageRole
from autobyteus.memory.compaction_snapshot_builder import CompactionSnapshotBuilder
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore


class _Renderer(BasePromptRenderer):
    async def render(self, messages):
        return [{"role": m.role.value, "content": m.content} for m in messages]


class _Summarizer:
    def summarize(self, traces):
        return type("Result", (), {"episodic_summary": "Summary", "semantic_facts": []})


@pytest.mark.asyncio
async def test_prepare_request_triggers_compaction_when_budget_exceeded(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_trigger")
    policy = CompactionPolicy(trigger_ratio=0.5, raw_tail_turns=1)
    manager = MemoryManager(store=store, compaction_policy=policy)

    # inject compactor with deterministic summarizer
    from autobyteus.memory.compaction.compactor import Compactor

    manager.compactor = Compactor(store=store, policy=policy, summarizer=_Summarizer())

    store.add(
        [
            RawTraceItem(
                id="rt_1",
                ts=time.time(),
                turn_id="turn_0001",
                seq=1,
                trace_type="user",
                content="old",
                source_event="LLMUserMessageReadyEvent",
            ),
            RawTraceItem(
                id="rt_2",
                ts=time.time(),
                turn_id="turn_0002",
                seq=1,
                trace_type="user",
                content="newer",
                source_event="LLMUserMessageReadyEvent",
            ),
        ]
    )

    assembler = LLMRequestAssembler(
        memory_manager=manager,
        renderer=_Renderer(),
        compaction_snapshot_builder=CompactionSnapshotBuilder(),
    )
    manager.request_compaction()

    request = await assembler.prepare_request(
        processed_user_input="current input",
        current_turn_id="turn_0003",
        system_prompt="System prompt",
    )

    assert request.did_compact is True
    assert manager.working_context_snapshot.epoch_id == 2
    assert [m.role for m in request.messages][:2] == [MessageRole.SYSTEM, MessageRole.USER]
    assert "[MEMORY:EPISODIC]" in request.messages[1].content
