import time

from autobyteus.llm.utils.messages import MessageRole
from autobyteus.memory.compaction_snapshot_builder import CompactionSnapshotBuilder
from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.retrieval.memory_bundle import MemoryBundle


def test_compaction_snapshot_builder_formats_sections():
    builder = CompactionSnapshotBuilder()
    bundle = MemoryBundle(
        episodic=[EpisodicItem(id="ep_1", ts=time.time(), turn_ids=["turn_0001"], summary="Did a thing.")],
        semantic=[SemanticItem(id="sem_1", ts=time.time(), fact="Use pytest.")],
    )
    raw_tail = [
        RawTraceItem(
            id="rt_1",
            ts=time.time(),
            turn_id="turn_0002",
            seq=1,
            trace_type="user",
            content="Hello",
            source_event="LLMUserMessageReadyEvent",
        ),
        RawTraceItem(
            id="rt_2",
            ts=time.time(),
            turn_id="turn_0002",
            seq=2,
            trace_type="tool_call",
            content="",
            source_event="PendingToolInvocationEvent",
            tool_name="list_directory",
            tool_call_id="call_1",
            tool_args={"path": "src"},
        ),
        RawTraceItem(
            id="rt_3",
            ts=time.time(),
            turn_id="turn_0002",
            seq=3,
            trace_type="tool_result",
            content="",
            source_event="ToolResultEvent",
            tool_name="list_directory",
            tool_call_id="call_1",
            tool_result=["a.py", "b.py"],
        ),
    ]

    messages = builder.build(
        system_prompt="System prompt",
        bundle=bundle,
        raw_tail=raw_tail,
    )

    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]
    summary_text = messages[1].content
    assert "[MEMORY:EPISODIC]" in summary_text
    assert "Did a thing." in summary_text
    assert "[MEMORY:SEMANTIC]" in summary_text
    assert "Use pytest." in summary_text
    assert "[RECENT TURNS]" in summary_text
    assert "list_directory" in summary_text
    assert "TOOL:" in summary_text
    assert "->" in summary_text
