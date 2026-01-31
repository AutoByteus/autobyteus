import time
from types import SimpleNamespace

import pytest

from autobyteus.agent.llm_request_assembler import LLMRequestAssembler
from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.memory.active_transcript import ActiveTranscript
from autobyteus.memory.compaction_snapshot_builder import CompactionSnapshotBuilder
from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.retrieval.memory_bundle import MemoryBundle


class FakeRenderer(BasePromptRenderer):
    async def render(self, messages):
        return [{"role": m.role.value, "content": m.content} for m in messages]


class FakeMemoryManager:
    def __init__(self, raw_tail=None):
        self.active_transcript = ActiveTranscript()
        self.compaction_policy = CompactionPolicy()
        self.compactor = SimpleNamespace()
        self.compactor.select_compaction_window = lambda: []
        self.compactor.compact = lambda _turns: None
        self.retriever = SimpleNamespace()
        self.retriever.retrieve = lambda max_episodic, max_semantic: MemoryBundle()
        self._raw_tail = raw_tail or []
        self.compaction_required = False

    def request_compaction(self):
        self.compaction_required = True

    def clear_compaction_request(self):
        self.compaction_required = False

    def get_transcript_messages(self):
        return self.active_transcript.build_messages()

    def reset_transcript(self, snapshot_messages):
        self.active_transcript.reset(snapshot_messages)

    def get_raw_tail(self, tail_turns, exclude_turn_id=None):
        if exclude_turn_id:
            return [item for item in self._raw_tail if item.turn_id != exclude_turn_id]
        return list(self._raw_tail)


@pytest.mark.asyncio
async def test_prepare_request_no_compaction():
    memory_manager = FakeMemoryManager()
    renderer = FakeRenderer()
    assembler = LLMRequestAssembler(
        memory_manager=memory_manager,
        renderer=renderer,
    )

    request = await assembler.prepare_request(
        processed_user_input="hello",
        system_prompt="System prompt",
    )

    assert request.did_compact is False
    assert [m.role for m in request.messages] == [MessageRole.SYSTEM, MessageRole.USER]
    assert memory_manager.active_transcript.build_messages() == request.messages


@pytest.mark.asyncio
async def test_prepare_request_compacts_and_resets_transcript():
    raw_tail = [
        RawTraceItem(
            id="rt_1",
            ts=time.time(),
            turn_id="turn_0001",
            seq=1,
            trace_type="user",
            content="Old",
            source_event="LLMUserMessageReadyEvent",
        )
    ]
    memory_manager = FakeMemoryManager(raw_tail=raw_tail)
    memory_manager.compaction_policy = CompactionPolicy(trigger_ratio=0.1)
    memory_manager.compactor.select_compaction_window = lambda: ["turn_0001"]
    memory_manager.compactor.compact = lambda _turns: None
    memory_manager.retriever.retrieve = lambda max_episodic, max_semantic: MemoryBundle(
        episodic=[EpisodicItem(id="ep_1", ts=time.time(), turn_ids=["turn_0001"], summary="Did a thing.")],
        semantic=[SemanticItem(id="sem_1", ts=time.time(), fact="Use pytest.")],
    )

    renderer = FakeRenderer()
    assembler = LLMRequestAssembler(
        memory_manager=memory_manager,
        renderer=renderer,
        compaction_snapshot_builder=CompactionSnapshotBuilder(),
    )
    memory_manager.request_compaction()

    request = await assembler.prepare_request(
        processed_user_input="new input",
        current_turn_id="turn_0002",
        system_prompt="System prompt",
    )

    assert request.did_compact is True
    assert memory_manager.active_transcript.epoch_id == 2
    assert memory_manager.active_transcript.last_compaction_ts is not None
    assert [m.role for m in request.messages] == [
        MessageRole.SYSTEM,
        MessageRole.USER,
        MessageRole.USER,
    ]
    assert "[MEMORY:EPISODIC]" in request.messages[1].content
