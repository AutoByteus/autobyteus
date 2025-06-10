import asyncio
import pytest
import logging
import concurrent.futures
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.agent.runtime.agent_runtime import AgentRuntime
from autobyteus.agent.context import AgentContext
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.context.phases import AgentOperationalPhase
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier
from autobyteus.agent.runtime.agent_worker import AgentWorker
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

# Using fixtures from autobyteus/tests/unit_tests/agent/conftest.py

@pytest.fixture
def mock_agent_context_for_runtime(agent_context): # Use the more complete fixture from conftest
    return agent_context

@pytest.fixture
def mock_event_handler_registry_for_runtime():
    return MagicMock(spec=EventHandlerRegistry)

@pytest.fixture
def mock_agent_worker_instance():
    worker_instance = MagicMock(spec_set=AgentWorker)
    worker_instance.start = MagicMock()
    worker_instance.stop = AsyncMock(return_value=None)
    worker_instance.is_alive = MagicMock(return_value=False)
    worker_instance.add_done_callback = MagicMock()
    worker_instance._stop_initiated = False 
    worker_instance._is_active = False
    return worker_instance

@pytest.fixture
def agent_runtime_with_mocks(mock_agent_context_for_runtime, mock_event_handler_registry_for_runtime, mock_agent_worker_instance):
    with patch('autobyteus.agent.runtime.agent_runtime.AgentWorker', return_value=mock_agent_worker_instance) as PatchedAgentWorkerClass:
        runtime = AgentRuntime(
            context=mock_agent_context_for_runtime,
            event_handler_registry=mock_event_handler_registry_for_runtime
        )
        runtime._PatchedAgentWorkerClass = PatchedAgentWorkerClass 
        runtime._mock_worker_instance = mock_agent_worker_instance
        yield runtime

@pytest.mark.asyncio
class TestAgentRuntime:

    def test_initialization_creates_and_configures_components(self, agent_runtime_with_mocks: AgentRuntime, mock_agent_context_for_runtime, mock_event_handler_registry_for_runtime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance 

        runtime._PatchedAgentWorkerClass.assert_called_once_with(
            context=mock_agent_context_for_runtime,
            event_handler_registry=mock_event_handler_registry_for_runtime
        )
        assert runtime._worker is mock_worker_instance
        mock_worker_instance.add_done_callback.assert_called_once_with(runtime._handle_worker_completion)

        assert isinstance(runtime.external_event_notifier, AgentExternalEventNotifier)
        assert runtime.external_event_notifier.agent_id == mock_agent_context_for_runtime.agent_id
        
        assert isinstance(runtime.phase_manager, AgentPhaseManager)
        assert runtime.phase_manager.context == mock_agent_context_for_runtime
        assert runtime.phase_manager.notifier == runtime.external_event_notifier
        assert mock_agent_context_for_runtime.state.phase_manager_ref == runtime.phase_manager

        # The phase manager sets this on its own __init__
        assert mock_agent_context_for_runtime.current_phase == AgentOperationalPhase.UNINITIALIZED

    def test_start_delegates_to_worker_and_notifies_phase(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance
        
        runtime.phase_manager.notify_runtime_starting_and_uninitialized = MagicMock()
        
        mock_worker_instance.is_alive.return_value = False 
        runtime.start()

        runtime.phase_manager.notify_runtime_starting_and_uninitialized.assert_called_once()
        mock_worker_instance.start.assert_called_once()

    def test_start_idempotency(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance

        mock_worker_instance.is_alive.return_value = True 
        runtime.phase_manager.notify_runtime_starting_and_uninitialized = MagicMock()
        mock_worker_instance.start.reset_mock()

        with patch('autobyteus.agent.runtime.agent_runtime.logger') as mock_logger:
            runtime.start()
            mock_logger.warning.assert_called_once()

        runtime.phase_manager.notify_runtime_starting_and_uninitialized.assert_not_called()
        mock_worker_instance.start.assert_not_called()

    async def test_stop_full_flow(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance
        context = agent_runtime_with_mocks.context

        mock_worker_instance.is_alive.return_value = True 

        runtime.phase_manager.notify_shutdown_initiated = MagicMock()
        runtime.phase_manager.notify_final_shutdown_complete = MagicMock()

        await runtime.stop(timeout=0.1)

        runtime.phase_manager.notify_shutdown_initiated.assert_called_once()
        mock_worker_instance.stop.assert_awaited_once_with(timeout=0.1)
        context.llm_instance.cleanup.assert_awaited_once()
        runtime.phase_manager.notify_final_shutdown_complete.assert_called_once()

    async def test_stop_when_worker_not_alive(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance
        
        mock_worker_instance.is_alive.return_value = False 
        mock_worker_instance._is_active = False 

        runtime.phase_manager.notify_shutdown_initiated = MagicMock()
        mock_worker_instance.stop.reset_mock()
        runtime.context.llm_instance.cleanup.reset_mock()
        runtime.phase_manager.notify_final_shutdown_complete = MagicMock()
        
        await runtime.stop(timeout=0.1)
        
        # Should return early
        runtime.phase_manager.notify_shutdown_initiated.assert_not_called() 
        mock_worker_instance.stop.assert_not_awaited()
        runtime.context.llm_instance.cleanup.assert_not_awaited()
        # But should still notify that it's complete
        runtime.phase_manager.notify_final_shutdown_complete.assert_called_once()

    def test_handle_worker_completion_success(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_future = MagicMock(spec=concurrent.futures.Future)
        mock_future.result = MagicMock(return_value=None) 
        
        runtime.phase_manager.notify_error_occurred = MagicMock()
        runtime.phase_manager.notify_final_shutdown_complete = MagicMock()
        
        with patch('autobyteus.agent.runtime.agent_runtime.logger') as mock_logger:
            runtime._handle_worker_completion(mock_future)
            successful_completion_logged = any(
                "Worker thread completed successfully" in call[0][0] 
                for call in mock_logger.info.call_args_list
            )
            assert successful_completion_logged
        
        runtime.phase_manager.notify_error_occurred.assert_not_called()
        runtime.phase_manager.notify_final_shutdown_complete.assert_called_once()

    @patch('autobyteus.agent.runtime.agent_runtime.traceback.format_exc', return_value="Mocked Traceback")
    def test_handle_worker_completion_with_exception(self, mock_format_exception, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        context = agent_runtime_with_mocks.context
        
        mock_future = MagicMock(spec=concurrent.futures.Future)
        test_exception = ValueError("Worker crashed")
        mock_future.result = MagicMock(side_effect=test_exception)

        context.current_phase = AgentOperationalPhase.IDLE 
        runtime.phase_manager.notify_error_occurred = MagicMock()
        runtime.phase_manager.notify_final_shutdown_complete = MagicMock()
        
        with patch('autobyteus.agent.runtime.agent_runtime.logger') as mock_logger:
            runtime._handle_worker_completion(mock_future)
            
            worker_exception_logged = any(
                f"Worker thread terminated with an exception: {test_exception}" in str(call[0][0])
                for call in mock_logger.error.call_args_list
            )
            assert worker_exception_logged

        runtime.phase_manager.notify_error_occurred.assert_called_once_with(
            "Worker thread exited unexpectedly.", "Mocked Traceback"
        )
        runtime.phase_manager.notify_final_shutdown_complete.assert_called_once()

    def test_current_phase_property(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        context = agent_runtime_with_mocks.context
        
        context.current_phase = AgentOperationalPhase.IDLE
        assert runtime.current_phase_property == AgentOperationalPhase.IDLE

        context.current_phase = AgentOperationalPhase.ERROR
        assert runtime.current_phase_property == AgentOperationalPhase.ERROR

    def test_is_running_property(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance

        mock_worker_instance.is_alive.return_value = True
        assert runtime.is_running

        mock_worker_instance.is_alive.return_value = False
        assert not runtime.is_running

    async def test_stop_no_llm_instance_does_not_fail(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        context = agent_runtime_with_mocks.context
        context.llm_instance = None # Remove the LLM instance

        mock_worker_instance = runtime._mock_worker_instance
        mock_worker_instance.is_alive.return_value = True 

        # This should run without raising an AttributeError
        await runtime.stop(timeout=0.1)
        
        mock_worker_instance.stop.assert_awaited_once_with(timeout=0.1)
