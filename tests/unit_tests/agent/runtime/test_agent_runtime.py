# file: autobyteus/tests/unit_tests/agent/runtime/test_agent_runtime.py
import asyncio
import pytest
import logging
import concurrent.futures
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.agent.runtime.agent_runtime import AgentRuntime
from autobyteus.agent.context import AgentContext, AgentContextRegistry
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.phases import AgentOperationalPhase, AgentPhaseManager
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier
from autobyteus.agent.runtime.agent_worker import AgentWorker

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
def mock_agent_context_registry():
    """Provides a patched AgentContextRegistry."""
    with patch('autobyteus.agent.runtime.agent_runtime.AgentContextRegistry') as PatchedRegistry:
        mock_instance = MagicMock(spec=AgentContextRegistry)
        PatchedRegistry.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def agent_runtime_with_mocks(mock_agent_context_for_runtime, mock_event_handler_registry_for_runtime, mock_agent_worker_instance, mock_agent_context_registry):
    with patch('autobyteus.agent.runtime.agent_runtime.AgentWorker', return_value=mock_agent_worker_instance) as PatchedAgentWorkerClass:
        runtime = AgentRuntime(
            context=mock_agent_context_for_runtime,
            event_handler_registry=mock_event_handler_registry_for_runtime
        )
        runtime._PatchedAgentWorkerClass = PatchedAgentWorkerClass 
        runtime._mock_worker_instance = mock_agent_worker_instance
        runtime._mock_context_registry = mock_agent_context_registry
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

        # Verify context registration on init
        runtime._mock_context_registry.register_context.assert_called_once_with(mock_agent_context_for_runtime)

        # The phase manager sets this on its own __init__
        assert mock_agent_context_for_runtime.current_phase == AgentOperationalPhase.UNINITIALIZED

    def test_start_delegates_to_worker(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance
        
        mock_worker_instance.is_alive.return_value = False 
        runtime.start()

        mock_worker_instance.start.assert_called_once()

    def test_start_idempotency(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance

        mock_worker_instance.is_alive.return_value = True 
        mock_worker_instance.start.reset_mock()

        with patch('autobyteus.agent.runtime.agent_runtime.logger') as mock_logger:
            runtime.start()
            mock_logger.warning.assert_called_once()

        mock_worker_instance.start.assert_not_called()

    async def test_stop_full_flow(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance
        context = agent_runtime_with_mocks.context

        mock_worker_instance.is_alive.return_value = True 

        await runtime.stop(timeout=0.1)

        runtime.phase_manager.notify_shutdown_initiated.assert_awaited_once()
        mock_worker_instance.stop.assert_awaited_once_with(timeout=0.1)
        # LLM cleanup is now handled by a shutdown step inside the worker, not directly by runtime.
        context.llm_instance.cleanup.assert_not_called()
        # Verify context is unregistered
        runtime._mock_context_registry.unregister_context.assert_called_once_with(context.agent_id)
        runtime.phase_manager.notify_final_shutdown_complete.assert_awaited_once()

    async def test_stop_when_worker_not_alive(self, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        mock_worker_instance = runtime._mock_worker_instance
        context = agent_runtime_with_mocks.context
        
        mock_worker_instance.is_alive.return_value = False 
        mock_worker_instance._is_active = False 

        runtime.phase_manager.notify_shutdown_initiated.reset_mock()
        mock_worker_instance.stop.reset_mock()
        context.llm_instance.cleanup.reset_mock()
        runtime.phase_manager.notify_final_shutdown_complete.reset_mock()
        
        await runtime.stop(timeout=0.1)
        
        # Should return early
        runtime.phase_manager.notify_shutdown_initiated.assert_not_awaited() 
        mock_worker_instance.stop.assert_not_awaited()
        context.llm_instance.cleanup.assert_not_called()
        # Should NOT unregister context, as it's assumed to be already unregistered if worker isn't active.
        runtime._mock_context_registry.unregister_context.assert_not_called()
        # But should still notify that it's complete
        runtime.phase_manager.notify_final_shutdown_complete.assert_awaited_once()

    @patch('asyncio.run')
    @patch('autobyteus.agent.runtime.agent_runtime.traceback.format_exc', return_value="Mocked Traceback")
    def test_handle_worker_completion_with_exception(self, mock_format_exception, mock_asyncio_run, agent_runtime_with_mocks: AgentRuntime):
        runtime = agent_runtime_with_mocks
        context = agent_runtime_with_mocks.context
        
        mock_future = MagicMock(spec=concurrent.futures.Future)
        test_exception = ValueError("Worker crashed")
        mock_future.result = MagicMock(side_effect=test_exception)

        context.current_phase = AgentOperationalPhase.IDLE 
        
        with patch('autobyteus.agent.runtime.agent_runtime.logger') as mock_logger:
            runtime._handle_worker_completion(mock_future)
            
            worker_exception_logged = any(
                f"Worker thread terminated with an exception: {test_exception}" in str(call[0][0])
                for call in mock_logger.error.call_args_list
            )
            assert worker_exception_logged
        
        assert mock_asyncio_run.call_count == 2
        
        error_call = mock_asyncio_run.call_args_list[0]
        final_call = mock_asyncio_run.call_args_list[1]

        assert error_call[0][0].__name__ == 'notify_error_occurred'
        assert final_call[0][0].__name__ == 'notify_final_shutdown_complete'

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
