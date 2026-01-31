from typing import Dict, List

from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.tool_interaction import ToolInteraction, ToolInteractionStatus


def build_tool_interactions(raw_traces: List[RawTraceItem]) -> List[ToolInteraction]:
    interactions: Dict[str, ToolInteraction] = {}

    for trace in raw_traces:
        if trace.trace_type not in {"tool_call", "tool_result"}:
            continue

        tool_call_id = trace.tool_call_id
        if not tool_call_id:
            continue

        interaction = interactions.get(tool_call_id)
        if interaction is None:
            interaction = ToolInteraction(
                tool_call_id=tool_call_id,
                turn_id=trace.turn_id,
                tool_name=trace.tool_name,
                arguments=None,
                result=None,
                error=None,
                status=ToolInteractionStatus.PENDING,
            )
            interactions[tool_call_id] = interaction

        if trace.trace_type == "tool_call":
            interaction.tool_name = trace.tool_name
            interaction.arguments = trace.tool_args
            if interaction.status == ToolInteractionStatus.PENDING and interaction.error:
                interaction.status = ToolInteractionStatus.ERROR
            continue

        if trace.trace_type == "tool_result":
            interaction.tool_name = trace.tool_name or interaction.tool_name
            interaction.result = trace.tool_result
            interaction.error = trace.tool_error
            interaction.status = (
                ToolInteractionStatus.ERROR if trace.tool_error else ToolInteractionStatus.SUCCESS
            )

    return list(interactions.values())
