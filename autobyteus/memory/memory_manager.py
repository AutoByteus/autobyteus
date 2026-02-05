import time
from typing import Optional, List

from autobyteus.agent.events.agent_events import ToolResultEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.messages import ToolCallSpec
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.retrieval.retriever import Retriever
from autobyteus.memory.store.base_store import MemoryStore
from autobyteus.memory.turn_tracker import TurnTracker
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot
from autobyteus.memory.tool_interaction_builder import build_tool_interactions
from autobyteus.memory.working_context_snapshot_serializer import WorkingContextSnapshotSerializer
from autobyteus.memory.store.working_context_snapshot_store import WorkingContextSnapshotStore


class MemoryManager:
    def __init__(
        self,
        store: MemoryStore,
        turn_tracker: Optional[TurnTracker] = None,
        compaction_policy: Optional[CompactionPolicy] = None,
        compactor: Optional[Compactor] = None,
        retriever: Optional[Retriever] = None,
        working_context_snapshot: Optional[WorkingContextSnapshot] = None,
        working_context_snapshot_store: Optional[WorkingContextSnapshotStore] = None,
    ):
        self.store = store
        self.turn_tracker = turn_tracker or TurnTracker()
        self.compaction_policy = compaction_policy or CompactionPolicy()
        self.compactor = compactor
        self.retriever = retriever or Retriever(store=store)
        self.memory_types = MemoryType
        self._seq_by_turn: dict[str, int] = {}
        self.working_context_snapshot = working_context_snapshot or WorkingContextSnapshot()
        self.compaction_required: bool = False
        self.working_context_snapshot_store = working_context_snapshot_store

    def start_turn(self) -> str:
        return self.turn_tracker.next_turn_id()

    def request_compaction(self) -> None:
        self.compaction_required = True

    def clear_compaction_request(self) -> None:
        self.compaction_required = False

    def _next_seq(self, turn_id: str) -> int:
        current = self._seq_by_turn.get(turn_id, 0) + 1
        self._seq_by_turn[turn_id] = current
        return current

    def ingest_user_message(self, llm_user_message: LLMUserMessage, turn_id: str, source_event: str) -> None:
        trace = RawTraceItem(
            id=f"rt_{int(time.time() * 1000)}",
            ts=time.time(),
            turn_id=turn_id,
            seq=self._next_seq(turn_id),
            trace_type="user",
            content=llm_user_message.content,
            source_event=source_event,
            media={
                "images": llm_user_message.image_urls or [],
                "audio": llm_user_message.audio_urls or [],
                "video": llm_user_message.video_urls or [],
            },
            tags=["processed"],
        )
        self.store.add([trace])

    def ingest_tool_intent(self, tool_invocation: ToolInvocation, turn_id: Optional[str] = None) -> None:
        effective_turn_id = tool_invocation.turn_id or turn_id
        if not effective_turn_id:
            raise ValueError("turn_id is required to ingest tool intent")
        trace = RawTraceItem(
            id=f"rt_{int(time.time() * 1000)}",
            ts=time.time(),
            turn_id=effective_turn_id,
            seq=self._next_seq(effective_turn_id),
            trace_type="tool_call",
            content="",
            source_event="PendingToolInvocationEvent",
            tool_name=tool_invocation.name,
            tool_call_id=tool_invocation.id,
            tool_args=tool_invocation.arguments,
        )
        self.store.add([trace])
        self.working_context_snapshot.append_tool_calls(
            [ToolCallSpec(id=tool_invocation.id, name=tool_invocation.name, arguments=tool_invocation.arguments)]
        )

    def ingest_tool_result(self, event: ToolResultEvent, turn_id: Optional[str] = None) -> None:
        effective_turn_id = event.turn_id or turn_id
        if not effective_turn_id:
            raise ValueError("turn_id is required to ingest tool result")
        trace = RawTraceItem(
            id=f"rt_{int(time.time() * 1000)}",
            ts=time.time(),
            turn_id=effective_turn_id,
            seq=self._next_seq(effective_turn_id),
            trace_type="tool_result",
            content="",
            source_event="ToolResultEvent",
            tool_name=event.tool_name,
            tool_call_id=event.tool_invocation_id,
            tool_args=event.tool_args,
            tool_result=event.result,
            tool_error=event.error,
        )
        self.store.add([trace])
        self.working_context_snapshot.append_tool_result(
            tool_call_id=event.tool_invocation_id or "",
            tool_name=event.tool_name,
            tool_result=event.result,
            tool_error=event.error,
        )

    def ingest_assistant_response(self, response: CompleteResponse, turn_id: str, source_event: str) -> None:
        trace = RawTraceItem(
            id=f"rt_{int(time.time() * 1000)}",
            ts=time.time(),
            turn_id=turn_id,
            seq=self._next_seq(turn_id),
            trace_type="assistant",
            content=response.content or "",
            source_event=source_event,
            tags=["final"],
        )
        self.store.add([trace])
        if response.content or response.reasoning:
            self.working_context_snapshot.append_assistant(
                content=response.content,
                reasoning=response.reasoning,
            )
        self.persist_working_context_snapshot()

    def _get_raw_tail(self, tail_turns: int, exclude_turn_id: Optional[str] = None) -> List[RawTraceItem]:
        raw_items = self.store.list(MemoryType.RAW_TRACE)
        if tail_turns <= 0:
            return []

        ordered_turns = []
        seen = set()
        for item in raw_items:
            if not isinstance(item, RawTraceItem):
                continue
            if exclude_turn_id and item.turn_id == exclude_turn_id:
                continue
            if item.turn_id not in seen:
                seen.add(item.turn_id)
                ordered_turns.append(item.turn_id)

        if not ordered_turns:
            return []

        keep_turns = set(ordered_turns[-tail_turns:])
        tail_items = [
            item
            for item in raw_items
            if isinstance(item, RawTraceItem) and item.turn_id in keep_turns
        ]

        order_index = {turn_id: idx for idx, turn_id in enumerate(ordered_turns)}
        tail_items.sort(key=lambda item: (order_index.get(item.turn_id, 0), item.seq))
        return tail_items

    def get_raw_tail(self, tail_turns: int, exclude_turn_id: Optional[str] = None) -> List[RawTraceItem]:
        return self._get_raw_tail(tail_turns, exclude_turn_id=exclude_turn_id)

    def get_working_context_messages(self):
        return self.working_context_snapshot.build_messages()

    def reset_working_context_snapshot(self, snapshot_messages):
        self.working_context_snapshot.reset(snapshot_messages)
        self.persist_working_context_snapshot()

    def persist_working_context_snapshot(self) -> None:
        if not self.working_context_snapshot_store:
            return
        agent_id = getattr(self.working_context_snapshot_store, "agent_id", None) or getattr(self.store, "agent_id", None)
        if not agent_id:
            return
        metadata = {
            "schema_version": 1,
            "agent_id": agent_id,
            "epoch_id": self.working_context_snapshot.epoch_id,
            "last_compaction_ts": self.working_context_snapshot.last_compaction_ts,
        }
        payload = WorkingContextSnapshotSerializer.serialize(self.working_context_snapshot, metadata)
        self.working_context_snapshot_store.write(agent_id, payload)


    def get_tool_interactions(self, turn_id: Optional[str] = None):
        raw_items = self.store.list(MemoryType.RAW_TRACE)
        if turn_id:
            raw_items = [
                item for item in raw_items
                if isinstance(item, RawTraceItem) and item.turn_id == turn_id
            ]
        return build_tool_interactions([item for item in raw_items if isinstance(item, RawTraceItem)])
