import os
import time

import pytest

from autobyteus.agent.llm_request_assembler import LLMRequestAssembler
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.prompt_renderers.openai_chat_renderer import OpenAIChatRenderer
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore
from tests.integration_tests.agent.compaction_real_summarizer import RealCompactionSummarizer


@pytest.fixture
def lmstudio_llm():
    manual_model_id = os.getenv("LMSTUDIO_MODEL_ID")
    if manual_model_id:
        return LLMFactory.create_llm(model_identifier=manual_model_id)

    LLMFactory.reinitialize()
    models = LLMFactory.list_models_by_runtime(LLMRuntime.LMSTUDIO)
    if not models:
        pytest.skip("No LM Studio models found.")

    target_text_model = "qwen/qwen3-30b-a3b-2507"
    text_model = next((m for m in models if target_text_model in m.model_identifier), None)
    if not text_model:
        text_model = next((m for m in models if "vl" not in m.model_identifier.lower()), models[0])

    return LLMFactory.create_llm(model_identifier=text_model.model_identifier)


@pytest.mark.asyncio
async def test_memory_compaction_real_scenario_flow(tmp_path, lmstudio_llm):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_compact_scenario")
    policy = CompactionPolicy(raw_tail_turns=1, trigger_ratio=0.1)
    summarizer = RealCompactionSummarizer(lmstudio_llm)
    compactor = Compactor(store=store, policy=policy, summarizer=summarizer)
    memory_manager = MemoryManager(store=store, compaction_policy=policy, compactor=compactor)

    # Turn 1: initial idea
    turn_1 = memory_manager.start_turn()
    memory_manager.ingest_user_message(
        LLMUserMessage(content="Idea: Approach-ALPHA keeps all raw traces forever."),
        turn_id=turn_1,
        source_event="LLMUserMessageReadyEvent",
    )
    memory_manager.ingest_assistant_response(
        response=type("Resp", (), {"content": "We can try Approach-ALPHA first.", "reasoning": None}),
        turn_id=turn_1,
        source_event="LLMCompleteResponseReceivedEvent",
    )

    # Turn 2: discard idea
    turn_2 = memory_manager.start_turn()
    memory_manager.ingest_user_message(
        LLMUserMessage(content="DROPPED: Approach-ALPHA caused context overflow."),
        turn_id=turn_2,
        source_event="LLMUserMessageReadyEvent",
    )
    memory_manager.ingest_assistant_response(
        response=type("Resp", (), {"content": "We will not use Approach-ALPHA.", "reasoning": None}),
        turn_id=turn_2,
        source_event="LLMCompleteResponseReceivedEvent",
    )

    # Turn 3: final decision
    turn_3 = memory_manager.start_turn()
    memory_manager.ingest_user_message(
        LLMUserMessage(
            content="DECISION: Use Approach-BETA (compaction + episodic/semantic). Constraint: keep raw tail 2 turns."
        ),
        turn_id=turn_3,
        source_event="LLMUserMessageReadyEvent",
    )
    memory_manager.ingest_assistant_response(
        response=type("Resp", (), {"content": "Proceeding with Approach-BETA.", "reasoning": None}),
        turn_id=turn_3,
        source_event="LLMCompleteResponseReceivedEvent",
    )

    # Current turn triggers compaction
    current_turn = memory_manager.start_turn()
    current_user = LLMUserMessage(content="Please respond with pong.")
    memory_manager.ingest_user_message(
        current_user,
        turn_id=current_turn,
        source_event="LLMUserMessageReadyEvent",
    )

    assembler = LLMRequestAssembler(
        memory_manager=memory_manager,
        renderer=OpenAIChatRenderer(),
    )
    memory_manager.request_compaction()

    request = await assembler.prepare_request(
        processed_user_input=current_user,
        current_turn_id=current_turn,
        system_prompt="System prompt",
    )

    assert request.did_compact is True

    episodic_items = store.list(MemoryType.EPISODIC)
    semantic_items = store.list(MemoryType.SEMANTIC)
    assert episodic_items

    summary_text = episodic_items[0].summary
    assert "Approach-BETA" in summary_text
    assert "Approach-ALPHA" in summary_text

    payload = summarizer.last_payload or {}
    decisions = payload.get("decisions", [])
    constraints = payload.get("constraints", [])
    assert any("Approach-BETA" in decision for decision in decisions)
    assert any("raw tail" in constraint.lower() or "2 turns" in constraint.lower() for constraint in constraints)

    await lmstudio_llm.cleanup()
