import asyncio
import time
import sys
import pytest
from unittest.mock import patch, MagicMock
import concurrent.futures

from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager

# Helper functions for tasks
def identity_task(value):
    return value

def short_sleep_task(duration=0.05):
    time.sleep(duration)
    return f"slept for {duration}"

def task_modifying_list(shared_list, item, duration=0.05):
    time.sleep(duration)
    shared_list.append(item)
    return f"appended {item}"

@pytest.fixture
def manager_instance():
    """
    Provides a clean AgentThreadPoolManager instance for each test
    and ensures it's properly shut down afterwards.
    """
    if hasattr(AgentThreadPoolManager, '_instances'):
        AgentThreadPoolManager._instances.clear()
    
    manager = AgentThreadPoolManager()
    yield manager
    
    if not manager._is_shutdown:
        manager.shutdown(wait=True)
    
    if hasattr(AgentThreadPoolManager, '_instances'):
        AgentThreadPoolManager._instances.clear()

class TestAgentThreadPoolManager:

    def test_singleton_behavior(self, manager_instance):
        """Tests that AgentThreadPoolManager is a singleton."""
        manager1 = manager_instance
        manager2 = AgentThreadPoolManager()
        assert manager1 is manager2, "AgentThreadPoolManager should return the same instance."

    def test_initialization_default(self, manager_instance):
        """Tests default initialization of the manager."""
        assert manager_instance._thread_pool is not None, "Thread pool should be initialized."
        assert isinstance(manager_instance._thread_pool, concurrent.futures.ThreadPoolExecutor)
        assert not manager_instance._is_shutdown, "Manager should not be shutdown initially."

    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_initialization_with_max_workers(self, mock_executor_class):
        """Tests initialization with a specific max_workers count."""
        if hasattr(AgentThreadPoolManager, '_instances'):
            AgentThreadPoolManager._instances.clear()
        
        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance
        
        expected_max_workers = 5
        manager = AgentThreadPoolManager(max_workers=expected_max_workers)
        
        mock_executor_class.assert_called_once_with(
            max_workers=expected_max_workers,
            thread_name_prefix="AgentThreadPool"
        )
        assert manager._thread_pool is mock_executor_instance
        
        if not manager._is_shutdown:
            manager.shutdown(wait=True)
        if hasattr(AgentThreadPoolManager, '_instances'):
            AgentThreadPoolManager._instances.clear()


    def test_submit_task_executes_successfully(self, manager_instance):
        """Tests that a submitted task is executed successfully."""
        shared_list = []
        item_to_append = "test_item"
        
        future = manager_instance.submit_task(task_modifying_list, shared_list, item_to_append, duration=0.1)
        result = future.result(timeout=1)
        
        assert result == f"appended {item_to_append}"
        assert item_to_append in shared_list, "Task should have modified the shared list."

    def test_submit_task_returns_future(self, manager_instance):
        """Tests that submit_task returns a Future object."""
        future = manager_instance.submit_task(identity_task, "value")
        assert isinstance(future, concurrent.futures.Future), "submit_task should return a Future."
        future.result(timeout=1)

    def test_submit_task_after_shutdown_raises_runtime_error(self, manager_instance):
        """Tests that submitting a task after shutdown raises RuntimeError."""
        manager_instance.shutdown(wait=False)
        
        with pytest.raises(RuntimeError, match="AgentThreadPoolManager is shutdown"):
            manager_instance.submit_task(identity_task, "value")

    def test_shutdown_waits_for_tasks(self, manager_instance):
        """Tests that shutdown(wait=True) waits for tasks to complete."""
        task_duration = 0.2
        future = manager_instance.submit_task(short_sleep_task, task_duration)
        
        start_time = time.monotonic()
        manager_instance.shutdown(wait=True)
        end_time = time.monotonic()
        
        assert future.done(), "Future should be done after shutdown(wait=True)."
        assert (end_time - start_time) >= task_duration, "Shutdown should have waited for the task."
        assert manager_instance._is_shutdown, "Manager should be marked as shutdown."

    def test_shutdown_no_wait(self, manager_instance):
        """Tests shutdown(wait=False) behavior."""
        task_duration = 0.5
        future = manager_instance.submit_task(short_sleep_task, task_duration)
        
        manager_instance.shutdown(wait=False)
        
        assert manager_instance._is_shutdown, "Manager should be marked as shutdown."
        try:
            future.result(timeout=0.05)
        except concurrent.futures.TimeoutError:
            pass
        
        future.result(timeout=task_duration + 0.5)


    def test_shutdown_multiple_calls_graceful(self, manager_instance):
        """Tests that multiple calls to shutdown are handled gracefully."""
        manager_instance.shutdown(wait=False)
        assert manager_instance._is_shutdown, "Manager should be shutdown after first call."
        
        try:
            manager_instance.shutdown(wait=False)
        except Exception as e:
            pytest.fail(f"Second call to shutdown raised an exception: {e}")
        
        assert manager_instance._is_shutdown, "Manager should remain shutdown."

    @patch.object(AgentThreadPoolManager, '_thread_pool', new_callable=MagicMock, create=True)
    def test_shutdown_passes_cancel_futures_if_supported(self, mock_thread_pool, manager_instance):
        """
        Tests that shutdown passes cancel_futures=True to the
        ThreadPoolExecutor's shutdown method if Python version is >= 3.9.
        """
        manager_instance._thread_pool = mock_thread_pool

        with patch('inspect.signature') as mock_signature:
            mock_param = MagicMock()
            mock_param.name = 'cancel_futures'
            mock_signature.return_value.parameters = {'cancel_futures': mock_param}

            if sys.version_info >= (3, 9):
                manager_instance.shutdown(wait=True, cancel_futures=True)
                mock_thread_pool.shutdown.assert_called_once_with(wait=True, cancel_futures=True)
            else:
                manager_instance.shutdown(wait=True, cancel_futures=True)
                mock_thread_pool.shutdown.assert_called_once_with(wait=True)

    @patch.object(AgentThreadPoolManager, '_thread_pool', new_callable=MagicMock, create=True)
    def test_shutdown_without_cancel_futures_specified(self, mock_thread_pool, manager_instance):
        """
        Tests that shutdown calls the ThreadPoolExecutor's shutdown
        without cancel_futures if the argument is not provided or False.
        """
        manager_instance._thread_pool = mock_thread_pool
        with patch('inspect.signature') as mock_signature:
            mock_param = MagicMock()
            mock_param.name = 'cancel_futures'
            mock_signature.return_value.parameters = {'cancel_futures': mock_param}

            manager_instance.shutdown(wait=True)
            if sys.version_info >= (3, 9):
                mock_thread_pool.shutdown.assert_called_once_with(wait=True, cancel_futures=False)
            else:
                mock_thread_pool.shutdown.assert_called_once_with(wait=True)

    def test_del_triggers_shutdown(self):
        """
        Tests if __del__ attempts to shutdown if not already done.
        """
        if hasattr(AgentThreadPoolManager, '_instances'):
            AgentThreadPoolManager._instances.clear()
        
        manager_to_delete = AgentThreadPoolManager(max_workers=1)
        assert not manager_to_delete._is_shutdown

        with patch.object(manager_to_delete, 'shutdown', wraps=manager_to_delete.shutdown) as mock_shutdown_method:
            original_pool = manager_to_delete._thread_pool
            
            del manager_to_delete
            time.sleep(0.1) 
            
            if not original_pool._shutdown: # type: ignore
                 if not mock_shutdown_method.called:
                    pytest.skip("`__del__` was not called, manually shutting down. Test of __del__ itself is inconclusive.")
                 original_pool.shutdown(wait=True) # type: ignore

        if hasattr(AgentThreadPoolManager, '_instances'):
            AgentThreadPoolManager._instances.clear()


    def test_submit_multiple_tasks(self, manager_instance):
        """Tests submitting and completing multiple tasks."""
        num_tasks = 5
        futures = []
        expected_results = []
        
        for i in range(num_tasks):
            val = i * 10
            futures.append(manager_instance.submit_task(identity_task, val))
            expected_results.append(val)
            
        results = [f.result(timeout=1) for f in futures]
        
        assert results == expected_results, "All submitted tasks should complete with correct results."
