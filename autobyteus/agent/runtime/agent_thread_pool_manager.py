# file: autobyteus/autobyteus/agent/runtime/agent_thread_pool_manager.py
import asyncio
import logging
import concurrent.futures
from typing import TYPE_CHECKING, Optional, Callable, Any

from autobyteus.utils.singleton import SingletonMeta 

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

class AgentThreadPoolManager(metaclass=SingletonMeta): 
    """
    A singleton manager for a shared ThreadPoolExecutor.
    Used by agent components (like AgentWorker) to submit tasks 
    that need to run in a separate thread.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initializes the AgentThreadPoolManager's shared ThreadPoolExecutor.
        This __init__ will be called only once by SingletonMeta upon first instantiation.

        Args:
            max_workers: The maximum number of threads in the pool.
                         Defaults to None (Python's default).
        """
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="AgentThreadPool" 
        )
        self._is_shutdown = False 
        logger.info(f"Singleton AgentThreadPoolManager initialized its ThreadPoolExecutor (max_workers={max_workers or 'default'}).")

    def submit_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> concurrent.futures.Future:
        """
        Submits a callable to be executed in the shared thread pool.

        Args:
            func: The callable to execute.
            *args: Positional arguments for the callable.
            **kwargs: Keyword arguments for the callable.

        Returns:
            A concurrent.futures.Future representing the execution of the callable.
        
        Raises:
            RuntimeError: If the manager is shutdown.
        """
        if self._is_shutdown: # pragma: no cover
            raise RuntimeError("AgentThreadPoolManager is shutdown. Cannot submit new tasks.")
        
        func_name = getattr(func, '__name__', repr(func))
        logger.debug(f"AgentThreadPoolManager submitting task '{func_name}' to thread pool.")
        
        future = self._thread_pool.submit(func, *args, **kwargs)
        return future

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """
        Shuts down the shared thread pool. This should typically be called at application exit.

        Args:
            wait: If True, wait for all submitted tasks to complete.
            cancel_futures: If True, attempt to cancel pending futures (Python 3.9+).
        """
        if self._is_shutdown: # pragma: no cover
            logger.info("AgentThreadPoolManager's shared ThreadPoolExecutor already requested to shutdown or is shutdown.")
            return

        logger.info(f"AgentThreadPoolManager shutting down shared ThreadPoolExecutor (wait={wait}, cancel_futures={cancel_futures})...")
        self._is_shutdown = True 
        
        import inspect
        sig = inspect.signature(self._thread_pool.shutdown)
        if 'cancel_futures' in sig.parameters:
             self._thread_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
        else: 
             self._thread_pool.shutdown(wait=wait)

        logger.info("AgentThreadPoolManager shared ThreadPoolExecutor shutdown process complete.")

    def __del__(self): # pragma: no cover
        if not self._is_shutdown:
            logger.warning("AgentThreadPoolManager deleted without explicit shutdown. Attempting non-waiting shutdown of thread pool.")
            self.shutdown(wait=False)
