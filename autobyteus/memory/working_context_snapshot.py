import time
from typing import List, Optional, Iterable, Any

from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)


class WorkingContextSnapshot:
    def __init__(self, initial_messages: Optional[Iterable[Message]] = None):
        self._messages: List[Message] = list(initial_messages) if initial_messages else []
        self.epoch_id: int = 1
        self.last_compaction_ts: Optional[float] = None

    def append_message(self, message: Message) -> None:
        self._messages.append(message)

    def append_user(self, content: str) -> None:
        self._messages.append(Message(role=MessageRole.USER, content=content))

    def append_assistant(self, content: Optional[str], reasoning: Optional[str] = None) -> None:
        self._messages.append(
            Message(
                role=MessageRole.ASSISTANT,
                content=content,
                reasoning_content=reasoning,
            )
        )

    def append_tool_calls(self, tool_calls: List[ToolCallSpec]) -> None:
        self._messages.append(
            Message(
                role=MessageRole.ASSISTANT,
                content=None,
                tool_payload=ToolCallPayload(tool_calls=tool_calls),
            )
        )

    def append_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        tool_result: Any,
        tool_error: Optional[str] = None,
    ) -> None:
        self._messages.append(
            Message(
                role=MessageRole.TOOL,
                content=None,
                tool_payload=ToolResultPayload(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    tool_result=tool_result,
                    tool_error=tool_error,
                ),
            )
        )

    def build_messages(self) -> List[Message]:
        return list(self._messages)

    def reset(self, snapshot_messages: Iterable[Message], last_compaction_ts: Optional[float] = None) -> None:
        self._messages = list(snapshot_messages)
        self.epoch_id += 1
        self.last_compaction_ts = last_compaction_ts if last_compaction_ts is not None else time.time()
