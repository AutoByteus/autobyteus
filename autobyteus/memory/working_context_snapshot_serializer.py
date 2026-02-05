import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot


class WorkingContextSnapshotSerializer:
    @staticmethod
    def serialize(working_context_snapshot: WorkingContextSnapshot, metadata: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "schema_version": metadata.get("schema_version", 1),
            "agent_id": metadata.get("agent_id"),
            "epoch_id": metadata.get("epoch_id", working_context_snapshot.epoch_id),
            "last_compaction_ts": metadata.get("last_compaction_ts", working_context_snapshot.last_compaction_ts),
            "messages": [WorkingContextSnapshotSerializer._serialize_message(msg) for msg in working_context_snapshot.build_messages()],
        }
        return payload

    @staticmethod
    def deserialize(payload: Dict[str, Any]) -> Tuple[WorkingContextSnapshot, Dict[str, Any]]:
        messages = [
            WorkingContextSnapshotSerializer._deserialize_message(msg)
            for msg in payload.get("messages", [])
            if isinstance(msg, dict)
        ]
        snapshot = WorkingContextSnapshot(initial_messages=messages)
        metadata = {
            "schema_version": payload.get("schema_version"),
            "agent_id": payload.get("agent_id"),
            "epoch_id": payload.get("epoch_id"),
            "last_compaction_ts": payload.get("last_compaction_ts"),
        }
        if isinstance(metadata["epoch_id"], int):
            snapshot.epoch_id = metadata["epoch_id"]
        if metadata["last_compaction_ts"] is not None:
            snapshot.last_compaction_ts = metadata["last_compaction_ts"]
        return snapshot, metadata

    @staticmethod
    def validate(payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        if not isinstance(payload.get("schema_version"), int):
            return False
        if not isinstance(payload.get("agent_id"), str):
            return False
        messages = payload.get("messages")
        if not isinstance(messages, list):
            return False
        for msg in messages:
            if not isinstance(msg, dict):
                return False
            if not isinstance(msg.get("role"), str):
                return False
        return True

    @staticmethod
    def _serialize_message(message: Message) -> Dict[str, Any]:
        base = message.to_dict()
        if base.get("tool_payload"):
            base["tool_payload"] = WorkingContextSnapshotSerializer._normalize_tool_payload(base["tool_payload"])
        return base

    @staticmethod
    def _deserialize_message(data: Dict[str, Any]) -> Message:
        role = MessageRole(data.get("role"))
        tool_payload = WorkingContextSnapshotSerializer._deserialize_tool_payload(data.get("tool_payload"))
        return Message(
            role=role,
            content=data.get("content"),
            reasoning_content=data.get("reasoning_content"),
            image_urls=data.get("image_urls") or [],
            audio_urls=data.get("audio_urls") or [],
            video_urls=data.get("video_urls") or [],
            tool_payload=tool_payload,
        )

    @staticmethod
    def _normalize_tool_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        if "tool_calls" in payload:
            return {
                "tool_calls": [
                    {
                        "id": call.get("id"),
                        "name": call.get("name"),
                        "arguments": WorkingContextSnapshotSerializer._safe_json_value(call.get("arguments")),
                    }
                    for call in payload.get("tool_calls", [])
                ]
            }
        return {
            "tool_call_id": payload.get("tool_call_id"),
            "tool_name": payload.get("tool_name"),
            "tool_result": WorkingContextSnapshotSerializer._safe_json_value(payload.get("tool_result")),
            "tool_error": payload.get("tool_error"),
        }

    @staticmethod
    def _deserialize_tool_payload(payload: Optional[Dict[str, Any]]) -> Optional[Any]:
        if not payload:
            return None
        if "tool_calls" in payload:
            calls = []
            for call in payload.get("tool_calls", []) or []:
                calls.append(
                    ToolCallSpec(
                        id=str(call.get("id")),
                        name=str(call.get("name")),
                        arguments=call.get("arguments") or {},
                    )
                )
            return ToolCallPayload(tool_calls=calls)
        if "tool_call_id" in payload:
            return ToolResultPayload(
                tool_call_id=str(payload.get("tool_call_id")),
                tool_name=str(payload.get("tool_name")),
                tool_result=payload.get("tool_result"),
                tool_error=payload.get("tool_error"),
            )
        return None

    @staticmethod
    def _safe_json_value(value: Any) -> Any:
        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value)
