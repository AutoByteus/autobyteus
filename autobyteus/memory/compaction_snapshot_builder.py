from typing import List, Dict

from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.retrieval.memory_bundle import MemoryBundle
from autobyteus.memory.tool_interaction_builder import build_tool_interactions
from autobyteus.memory.models.tool_interaction import ToolInteractionStatus


class CompactionSnapshotBuilder:
    def build(self, system_prompt: str, bundle: MemoryBundle, raw_tail: List[RawTraceItem]) -> List[Message]:
        parts: List[str] = []

        if bundle.episodic:
            parts.append("[MEMORY:EPISODIC]")
            for idx, item in enumerate(bundle.episodic, start=1):
                parts.append(f"{idx}) {item.summary}")
            parts.append("")

        if bundle.semantic:
            parts.append("[MEMORY:SEMANTIC]")
            for item in bundle.semantic:
                parts.append(f"- {item.fact}")
            parts.append("")

        if raw_tail:
            parts.append("[RECENT TURNS]")
            parts.extend(self._format_recent_turns(raw_tail))
            parts.append("")

        summary_text = "\n".join(parts).strip()

        messages = [Message(role=MessageRole.SYSTEM, content=system_prompt)]
        if summary_text:
            messages.append(Message(role=MessageRole.USER, content=summary_text))
        return messages

    def _format_recent_turns(self, raw_tail: List[RawTraceItem]) -> List[str]:
        lines: List[str] = []
        interactions = build_tool_interactions(raw_tail)
        interaction_ids = {interaction.tool_call_id for interaction in interactions}

        first_trace_by_call_id: Dict[str, RawTraceItem] = {}
        for item in raw_tail:
            if item.tool_call_id and item.tool_call_id not in first_trace_by_call_id:
                first_trace_by_call_id[item.tool_call_id] = item

        def sort_key(interaction):
            trace = first_trace_by_call_id.get(interaction.tool_call_id)
            return trace.seq if trace else 0

        for interaction in sorted(interactions, key=sort_key):
            trace = first_trace_by_call_id.get(interaction.tool_call_id)
            if trace:
                prefix = f"({trace.turn_id}:{trace.seq}) TOOL:"
            else:
                prefix = "(unknown) TOOL:"

            if interaction.status == ToolInteractionStatus.PENDING:
                result_text = "pending"
            elif interaction.status == ToolInteractionStatus.ERROR:
                result_text = interaction.error or "error"
            else:
                result_text = interaction.result

            lines.append(
                f"{prefix} {interaction.tool_name} {interaction.arguments} -> {result_text}"
            )

        for item in raw_tail:
            if item.trace_type in {"tool_call", "tool_result"} and item.tool_call_id in interaction_ids:
                continue
            lines.append(self._format_raw_trace(item))

        return lines

    def _format_raw_trace(self, item: RawTraceItem) -> str:
        prefix = f"({item.turn_id}:{item.seq}) {item.trace_type.upper()}:"
        if item.trace_type == "tool_call":
            return f"{prefix} {item.tool_name} {item.tool_args}"
        if item.trace_type == "tool_result":
            result = item.tool_error if item.tool_error else item.tool_result
            return f"{prefix} {item.tool_name} {result}"
        return f"{prefix} {item.content}"
