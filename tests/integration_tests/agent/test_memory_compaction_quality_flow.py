import time

import pytest

from autobyteus.agent.llm_request_assembler import LLMRequestAssembler
from autobyteus.llm.prompt_renderers.openai_chat_renderer import OpenAIChatRenderer
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore


class _Summarizer(Summarizer):
    def summarize(self, traces):
        summary = " | ".join(t.content for t in traces if t.content)
        return CompactionResult(
            episodic_summary=summary or "summary",
            semantic_facts=[{"fact": "user wants pong", "confidence": 0.7}],
        )



def _trace(
    turn_id: str,
    seq: int,
    trace_type: str,
    content: str = "",
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    tool_args: dict | None = None,
    tool_result: object | None = None,
):
    return RawTraceItem(
        id=f"rt_{turn_id}_{seq}",
        ts=time.time(),
        turn_id=turn_id,
        seq=seq,
        trace_type=trace_type,
        content=content,
        source_event="TestEvent",
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_args=tool_args,
        tool_result=tool_result,
    )


@pytest.mark.asyncio
async def test_memory_compaction_quality_flow(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_compact_quality")
    policy = CompactionPolicy(raw_tail_turns=2, trigger_ratio=0.1)
    compactor = Compactor(store=store, policy=policy, summarizer=_Summarizer())
    memory_manager = MemoryManager(store=store, compaction_policy=policy, compactor=compactor)

    # Seed turn_0001 (to be compacted)
    turn_0_id = memory_manager.start_turn()
    store.add(
        [
            _trace(turn_0_id, 1, "user", "turn 0 user"),
            _trace(turn_0_id, 2, "assistant", "turn 0 assistant"),
        ]
    )

    # Seed turn_0002 (raw tail with tool interaction)
    turn_1_id = memory_manager.start_turn()
    store.add(
        [
            _trace(turn_1_id, 1, "user", "turn 1 user"),
            _trace(
                turn_1_id,
                2,
                "tool_call",
                tool_name="write_file",
                tool_call_id="call_1",
                tool_args={"path": "hello.py"},
            ),
            _trace(
                turn_1_id,
                3,
                "tool_result",
                tool_name="write_file",
                tool_call_id="call_1",
                tool_result="ok",
            ),
            _trace(turn_1_id, 4, "assistant", "turn 1 assistant"),
        ]
    )

    # Current turn
    current_turn_id = memory_manager.start_turn()
    current_user = LLMUserMessage(content="Please respond with pong.")
    memory_manager.ingest_user_message(
        current_user,
        turn_id=current_turn_id,
        source_event="LLMUserMessageReadyEvent",
    )

    assembler = LLMRequestAssembler(
        memory_manager=memory_manager,
        renderer=OpenAIChatRenderer(),
    )
    memory_manager.request_compaction()

    request = await assembler.prepare_request(
        processed_user_input=current_user,
        current_turn_id=current_turn_id,
        system_prompt="System prompt",
    )

    assert request.did_compact is True

    episodic_items = store.list(MemoryType.EPISODIC)
    semantic_items = store.list(MemoryType.SEMANTIC)
    assert len(episodic_items) == 1
    assert "turn 0 user" in episodic_items[0].summary
    assert len(semantic_items) == 1
    assert semantic_items[0].fact == "user wants pong"

    # Snapshot prompt quality
    assert len(request.messages) == 3
    snapshot = request.messages[1].content
    assert "[MEMORY:EPISODIC]" in snapshot
    assert "turn 0 assistant" in snapshot
    assert "[MEMORY:SEMANTIC]" in snapshot
    assert "user wants pong" in snapshot
    assert "[RECENT TURNS]" in snapshot
    assert "TOOL:" in snapshot
    assert "write_file" in snapshot
