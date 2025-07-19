# file: autobyteus/tests/unit_tests/agent/shutdown_steps/test_llm_instance_cleanup_step.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.shutdown_steps.llm_instance_cleanup_step import LLMInstanceCleanupStep
from autobyteus.agent.context import AgentContext
from autobyteus.llm.base_llm import BaseLLM

@pytest.fixture
def llm_cleanup_step():
    """Provides a clean instance of LLMInstanceCleanupStep."""
    return LLMInstanceCleanupStep()

@pytest.mark.asyncio
async def test_execute_success_with_async_cleanup(llm_cleanup_step: LLMInstanceCleanupStep, agent_context: AgentContext):
    """Tests success when the LLM instance has an async cleanup method."""
    mock_llm = MagicMock(spec=BaseLLM)
    mock_llm.cleanup = AsyncMock()
    agent_context.state.llm_instance = mock_llm

    success = await llm_cleanup_step.execute(agent_context)

    assert success is True
    mock_llm.cleanup.assert_awaited_once()

@pytest.mark.asyncio
async def test_execute_success_with_sync_cleanup(llm_cleanup_step: LLMInstanceCleanupStep, agent_context: AgentContext):
    """Tests success when the LLM instance has a synchronous cleanup method."""
    mock_llm = MagicMock(spec=BaseLLM)
    mock_llm.cleanup = MagicMock()
    agent_context.state.llm_instance = mock_llm

    success = await llm_cleanup_step.execute(agent_context)

    assert success is True
    mock_llm.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_execute_success_no_cleanup_method(llm_cleanup_step: LLMInstanceCleanupStep, agent_context: AgentContext, caplog):
    """Tests graceful success when the LLM instance lacks a cleanup method."""
    mock_llm = MagicMock(spec=BaseLLM)
    del mock_llm.cleanup
    agent_context.state.llm_instance = mock_llm

    with caplog.at_level(logging.DEBUG):
        success = await llm_cleanup_step.execute(agent_context)

    assert success is True
    assert "does not have a 'cleanup' method" in caplog.text

@pytest.mark.asyncio
async def test_execute_success_no_llm_instance(llm_cleanup_step: LLMInstanceCleanupStep, agent_context: AgentContext, caplog):
    """Tests graceful success when there is no LLM instance in the context."""
    agent_context.state.llm_instance = None

    with caplog.at_level(logging.DEBUG):
        success = await llm_cleanup_step.execute(agent_context)

    assert success is True
    assert "No LLM instance found in context. Skipping cleanup" in caplog.text

@pytest.mark.asyncio
async def test_execute_fails_on_exception(llm_cleanup_step: LLMInstanceCleanupStep, agent_context: AgentContext, caplog):
    """Tests that the step fails if the cleanup method raises an exception."""
    exception_message = "LLM client connection failed"
    mock_llm = MagicMock(spec=BaseLLM)
    mock_llm.cleanup = MagicMock(side_effect=RuntimeError(exception_message))
    agent_context.state.llm_instance = mock_llm

    with caplog.at_level(logging.ERROR):
        success = await llm_cleanup_step.execute(agent_context)

    assert success is False
    assert f"Error during LLM instance cleanup: {exception_message}" in caplog.text
