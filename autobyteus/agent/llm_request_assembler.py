from dataclasses import dataclass
from typing import Any, List, Optional, Union

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.memory.compaction_snapshot_builder import CompactionSnapshotBuilder
from autobyteus.memory.memory_manager import MemoryManager


@dataclass
class RequestPackage:
    messages: List[Message]
    rendered_payload: Any
    did_compact: bool


class LLMRequestAssembler:
    def __init__(
        self,
        memory_manager: MemoryManager,
        renderer: BasePromptRenderer,
        compaction_snapshot_builder: Optional[CompactionSnapshotBuilder] = None,
        max_episodic: int = 3,
        max_semantic: int = 20,
    ):
        self.memory_manager = memory_manager
        self.renderer = renderer
        self.compaction_snapshot_builder = compaction_snapshot_builder or CompactionSnapshotBuilder()
        self.max_episodic = max_episodic
        self.max_semantic = max_semantic

    async def prepare_request(
        self,
        processed_user_input: Union[str, LLMUserMessage],
        current_turn_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> RequestPackage:
        user_message = self._build_user_message(processed_user_input)
        self._ensure_system_prompt(system_prompt)

        did_compact = False
        policy = self.memory_manager.compaction_policy
        compactor = self.memory_manager.compactor

        if self.memory_manager.compaction_required and policy and compactor:
            turn_ids = compactor.select_compaction_window()
            if turn_ids:
                compactor.compact(turn_ids)
                bundle = self.memory_manager.retriever.retrieve(
                    max_episodic=self.max_episodic,
                    max_semantic=self.max_semantic,
                )
                raw_tail = self.memory_manager.get_raw_tail(
                    policy.raw_tail_turns,
                    exclude_turn_id=current_turn_id,
                )
                snapshot_messages = self.compaction_snapshot_builder.build(
                    system_prompt=system_prompt or "",
                    bundle=bundle,
                    raw_tail=raw_tail,
                )
                self.memory_manager.reset_working_context_snapshot(snapshot_messages)
                self.memory_manager.clear_compaction_request()
                did_compact = True

        self.memory_manager.working_context_snapshot.append_message(user_message)
        final_messages = self.memory_manager.get_working_context_messages()
        rendered_payload = await self.render_payload(final_messages)

        return RequestPackage(
            messages=final_messages,
            rendered_payload=rendered_payload,
            did_compact=did_compact,
        )

    async def render_payload(self, messages: List[Message]) -> Any:
        return await self.renderer.render(messages)

    def _build_user_message(self, processed_user_input: Union[str, LLMUserMessage]) -> Message:
        if isinstance(processed_user_input, LLMUserMessage):
            return Message(
                role=MessageRole.USER,
                content=processed_user_input.content,
                image_urls=processed_user_input.image_urls,
                audio_urls=processed_user_input.audio_urls,
                video_urls=processed_user_input.video_urls,
            )
        return Message(role=MessageRole.USER, content=str(processed_user_input))

    def _ensure_system_prompt(self, system_prompt: Optional[str]) -> None:
        if not system_prompt:
            return
        existing = self.memory_manager.get_working_context_messages()
        if not existing:
            self.memory_manager.working_context_snapshot.append_message(
                Message(role=MessageRole.SYSTEM, content=system_prompt)
            )
