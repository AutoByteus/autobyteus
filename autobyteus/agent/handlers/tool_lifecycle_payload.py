from typing import Any, Dict

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events.agent_events import ToolResultEvent


def build_tool_lifecycle_base_payload(
    agent_id: str,
    tool_name: str,
    invocation_id: str,
    turn_id: str | None,
) -> Dict[str, Any]:
    return {
        "agent_id": agent_id,
        "tool_name": tool_name,
        "invocation_id": invocation_id,
        "turn_id": turn_id,
    }


def build_tool_lifecycle_payload_from_invocation(
    agent_id: str,
    invocation: ToolInvocation,
) -> Dict[str, Any]:
    return build_tool_lifecycle_base_payload(
        agent_id=agent_id,
        tool_name=invocation.name,
        invocation_id=invocation.id,
        turn_id=invocation.turn_id,
    )


def build_tool_lifecycle_payload_from_result(
    agent_id: str,
    result: ToolResultEvent,
) -> Dict[str, Any]:
    return build_tool_lifecycle_base_payload(
        agent_id=agent_id,
        tool_name=result.tool_name,
        invocation_id=result.tool_invocation_id or "unknown_invocation",
        turn_id=result.turn_id,
    )
