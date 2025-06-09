# file: autobyteus/autobyteus/agent/runtime/agent_worker.py
import asyncio
import logging
import traceback
import threading 
import concurrent.futures
from typing import TYPE_CHECKING, Optional, Any, Callable, Awaitable 

from autobyteus.agent.context.phases import AgentOperationalPhase
from autobyteus.agent.events.agent_events import ( 
    BaseEvent,
    AgentErrorEvent, 
    AgentStoppedEvent,
)
# END_OF_STREAM_SENTINEL is no longer used by worker for output queues
from autobyteus.agent.events import WorkerEventDispatcher
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.handlers import EventHandlerRegistry 


logger = logging.getLogger(__name__)

class AgentWorker:
    """
    Encapsulates the core event processing loop for an agent.
    It manages its own execution in a dedicated thread obtained from the
    AgentThreadPoolManager, and runs its own asyncio event loop.
    Input queues are initialized as part of its bootstrap sequence.
    Output is handled via emitting events through AgentExternalEventNotifier.
    """

    def __init__(self,
                 context: 'AgentContext',
                 event_handler_registry: 'EventHandlerRegistry'): 
        self.context: 'AgentContext' = context
        
        self.phase_manager = self.context.phase_manager
        if not self.phase_manager: # pragma: no cover
            critical_msg = f"AgentWorker for '{self.context.agent_id}': AgentPhaseManager not found in context.state. Worker cannot function correctly."
            logger.critical(critical_msg)
            raise ValueError(critical_msg)

        self.worker_event_dispatcher = WorkerEventDispatcher(
            event_handler_registry=event_handler_registry, 
            phase_manager=self.phase_manager
        )
        
        self._thread_pool_manager: 'AgentThreadPoolManager' = AgentThreadPoolManager() 
        self._thread_future: Optional[concurrent.futures.Future] = None
        self._worker_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_stop_event: Optional[asyncio.Event] = None 
        
        self._is_active: bool = False 
        self._stop_initiated: bool = False 

        self._done_callbacks: list[Callable[[concurrent.futures.Future], None]] = []

        logger.info(f"AgentWorker initialized for agent_id '{self.context.agent_id}'. Input queues will be set up during bootstrap. Output via notifier.")

    def add_done_callback(self, callback: Callable[[concurrent.futures.Future], None]):
        """Adds a callback to be executed when the worker's thread completes."""
        if self._thread_future: 
            self._thread_future.add_done_callback(callback)
        else: 
            self._done_callbacks.append(callback)

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """
        Returns a reference to the worker's asyncio event loop.
        Returns None if the loop is not running or not yet initialized.
        """
        if self._worker_loop and self._worker_loop.is_running():
            return self._worker_loop
        return None

    def schedule_coroutine_on_worker_loop(self, coro_factory: Callable[[], Awaitable[Any]]) -> concurrent.futures.Future:
        """
        Schedules a coroutine (created by coro_factory) to be run on the worker's event loop.
        This is intended to be called from other threads.
        """
        worker_loop = self.get_worker_loop()
        if not worker_loop: # pragma: no cover
            logger.error(f"AgentWorker '{self.context.agent_id}': Worker event loop is not available or not running. Cannot schedule coroutine.")
            raise RuntimeError(f"AgentWorker '{self.context.agent_id}': Worker event loop is not available or not running. Cannot schedule coroutine.")
        
        return asyncio.run_coroutine_threadsafe(coro_factory(), worker_loop)


    def start(self) -> None:
        agent_id = self.context.agent_id
        if self._is_active or (self._thread_future and not self._thread_future.done()):
            logger.warning(f"AgentWorker '{agent_id}': Start called, but worker is already active or starting.")
            return

        logger.info(f"AgentWorker '{agent_id}': Starting...")
        self._is_active = True
        self._stop_initiated = False
        
        self._thread_future = self._thread_pool_manager.submit_task(self._run_managed_thread_loop)
        for cb in self._done_callbacks: 
            self._thread_future.add_done_callback(cb)
        self._done_callbacks.clear() 

        logger.info(f"AgentWorker '{agent_id}': Submitted to AgentThreadPoolManager's thread pool.")

    def _run_managed_thread_loop(self) -> None:
        thread_name = threading.current_thread().name
        agent_id = self.context.agent_id
        logger.info(f"AgentWorker '{agent_id}': Thread '{thread_name}' started. Setting up asyncio event loop.")
        
        try:
            self._worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._worker_loop)
            self._async_stop_event = asyncio.Event() 
            
            logger.info(f"AgentWorker '{agent_id}': Asyncio loop and stop event initialized in thread '{thread_name}'. Running async_run.")
            self._worker_loop.run_until_complete(self.async_run())

        except Exception as e: # pragma: no cover
            logger.error(f"AgentWorker '{agent_id}': Unhandled exception in _run_managed_thread_loop (thread '{thread_name}'): {e}", exc_info=True)
            if self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal():
                self.phase_manager.notify_error_occurred(f"Worker thread fatal error: {e}", traceback.format_exc())
        finally:
            if self._worker_loop:
                try:
                    all_tasks = asyncio.all_tasks(self._worker_loop)
                    if all_tasks: # pragma: no cover
                        logger.debug(f"AgentWorker '{agent_id}': Cancelling {len(all_tasks)} remaining tasks in worker loop.")
                        for task in all_tasks: task.cancel()
                        self._worker_loop.run_until_complete(asyncio.gather(*all_tasks, return_exceptions=True))
                    self._worker_loop.run_until_complete(self._worker_loop.shutdown_asyncgens())
                except Exception as e_shutdown: # pragma: no cover
                     logger.error(f"AgentWorker '{agent_id}': Error during worker loop shutdown procedures: {e_shutdown}", exc_info=True)
                finally:
                    self._worker_loop.close()
                    logger.info(f"AgentWorker '{agent_id}': Asyncio event loop for thread '{thread_name}' closed.")
                    self._worker_loop = None
            logger.info(f"AgentWorker '{agent_id}': Thread '{thread_name}' (_run_managed_thread_loop) finished.")
            self._is_active = False 

    async def _signal_internal_stop(self):
        agent_id = self.context.agent_id
        if self._async_stop_event and not self._async_stop_event.is_set():
            logger.debug(f"AgentWorker '{agent_id}': (_signal_internal_stop) Setting _async_stop_event.")
            self._async_stop_event.set()
            try:
                if self.context.state.input_event_queues:
                    await self.context.state.input_event_queues.enqueue_internal_system_event(AgentStoppedEvent())
                    logger.debug(f"AgentWorker '{agent_id}': (_signal_internal_stop) AgentStoppedEvent enqueued.")
                else: # pragma: no cover
                    logger.error(f"AgentWorker '{agent_id}': (_signal_internal_stop) Input event queues not available, cannot enqueue AgentStoppedEvent.")
            except Exception as e: # pragma: no cover
                logger.error(f"AgentWorker '{agent_id}': (_signal_internal_stop) Failed to enqueue AgentStoppedEvent: {e}", exc_info=True)
        elif self._async_stop_event and self._async_stop_event.is_set():
            logger.debug(f"AgentWorker '{agent_id}': (_signal_internal_stop) _async_stop_event was already set.")
        else: # pragma: no cover
             logger.error(f"AgentWorker '{agent_id}': (_signal_internal_stop) _async_stop_event not initialized!")


    async def stop(self, timeout: float = 10.0) -> None:
        agent_id = self.context.agent_id
        if not self._is_active or self._stop_initiated:
            logger.warning(f"AgentWorker '{agent_id}': Stop called, but worker is not active, already stopped, or stop is in progress.")
            if self._thread_future and not self._thread_future.done(): 
                 try: await asyncio.wrap_future(self._thread_future, timeout=timeout)
                 except asyncio.TimeoutError: logger.warning(f"AgentWorker '{agent_id}': Timeout (again) waiting for already stopping worker thread.")
            return

        logger.info(f"AgentWorker '{agent_id}': Stop requested (timeout: {timeout}s).")
        self._stop_initiated = True

        worker_loop_ref = self.get_worker_loop()
        if worker_loop_ref and self._async_stop_event: 
            logger.debug(f"AgentWorker '{agent_id}': Scheduling internal stop signal to worker's asyncio loop.")
            future = asyncio.run_coroutine_threadsafe(self._signal_internal_stop(), worker_loop_ref)
            try:
                future.result(timeout=1.0) 
                logger.debug(f"AgentWorker '{agent_id}': Internal stop signal dispatched to worker loop.")
            except concurrent.futures.TimeoutError: # pragma: no cover
                logger.warning(f"AgentWorker '{agent_id}': Timeout dispatching internal stop signal. Worker loop may be unresponsive.")
            except Exception as e: # pragma: no cover
                logger.error(f"AgentWorker '{agent_id}': Error dispatching internal stop signal: {e}", exc_info=True)
        else:
            logger.warning(f"AgentWorker '{agent_id}': Worker loop not running or stop event not available. Cannot dispatch internal stop signal. Thread future state: {self._thread_future.done() if self._thread_future else 'N/A'}")

        if self._thread_future:
            logger.debug(f"AgentWorker '{agent_id}': Waiting for worker thread to complete.")
            try:
                await asyncio.wrap_future(self._thread_future, timeout=timeout)
                logger.info(f"AgentWorker '{agent_id}': Worker thread completed.")
            except asyncio.TimeoutError: # pragma: no cover
                logger.warning(f"AgentWorker '{agent_id}': Timeout waiting for worker thread to complete. Thread may be stuck.")
            except asyncio.CancelledError: # pragma: no cover
                 logger.info(f"AgentWorker '{agent_id}': Waiting on worker thread future was cancelled.")
            except Exception as e: # pragma: no cover
                logger.error(f"AgentWorker '{agent_id}': Exception waiting for worker thread completion: {e}", exc_info=True)
        
        self._is_active = False
        logger.info(f"AgentWorker '{agent_id}': Stop process finished.")


    def is_alive(self) -> bool:
        """Checks if the worker's thread is currently active."""
        return self._thread_future is not None and not self._thread_future.done()

    async def async_run(self) -> None:
        agent_id = self.context.agent_id
        if not self._async_stop_event: # pragma: no cover
            logger.critical(f"AgentWorker '{agent_id}': _async_stop_event not initialized at start of async_run. This is a fatal setup error.")
            return 

        logger.info(f"AgentWorker '{agent_id}' async_run(): Loop starting. Waiting for events via queue...")

        try:
            while not self._async_stop_event.is_set(): 
                if not self.context.state.input_event_queues: 
                    if self._async_stop_event.is_set(): break # pragma: no cover
                    await asyncio.sleep(0.01) 
                    continue

                try:
                    queue_event_tuple = await asyncio.wait_for(
                        self.context.state.input_event_queues.get_next_input_event(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if self._async_stop_event.is_set(): break
                    
                    current_q_phase = self.context.current_phase
                    
                    # **FIX**: Do not automatically transition to IDLE if the agent is in a state
                    # that explicitly waits for external input, like AWAITING_TOOL_APPROVAL.
                    phases_that_wait_for_external_input = [
                        AgentOperationalPhase.AWAITING_TOOL_APPROVAL
                    ]
                    if current_q_phase in phases_that_wait_for_external_input:
                        continue # Simply continue the loop, waiting for the external event.

                    # Original logic for other processing phases that might be "stuck"
                    if current_q_phase and current_q_phase.is_processing() and \
                       not current_q_phase.is_terminal() and \
                       self.context.state.input_event_queues and \
                       all(q.empty() for _, q in self.context.state.input_event_queues._input_queues if q is not None):
                        if current_q_phase != AgentOperationalPhase.IDLE:
                            if self.phase_manager: self.phase_manager.notify_processing_complete_and_idle()
                    continue 
                except RuntimeError as e: 
                    if self.context.state.input_event_queues is None and "Input event queues have not been initialized" in str(e) : # pragma: no cover
                        if self._async_stop_event.is_set(): break
                        logger.log(logging.DEBUG if not self._async_stop_event.is_set() else logging.WARNING,
                                   f"AgentWorker '{agent_id}': Input queues not ready yet, sleeping. Stop event: {self._async_stop_event.is_set()}")
                        await asyncio.sleep(0.05)
                        continue
                    else: # pragma: no cover
                        logger.error(f"AgentWorker '{agent_id}': Unexpected RuntimeError in get_next_input_event: {e}", exc_info=True)
                        raise 
                except Exception as e_gnie: 
                    logger.error(f"AgentWorker '{agent_id}': Error in get_next_input_event: {e_gnie}", exc_info=True)
                    if self._async_stop_event.is_set(): break # pragma: no cover
                    await asyncio.sleep(0.1) 
                    continue


                if queue_event_tuple is None: # pragma: no cover
                    if self._async_stop_event.is_set(): break
                    continue

                _queue_name, event_obj = queue_event_tuple

                if not isinstance(event_obj, BaseEvent): # pragma: no cover
                    logger.warning(f"AgentWorker '{agent_id}': Non-BaseEvent from '{_queue_name}': {type(event_obj)}. Skipping.")
                    continue
                
                if isinstance(event_obj, AgentStoppedEvent): 
                    logger.debug(f"AgentWorker '{agent_id}': Processing AgentStoppedEvent in async_run.")
                
                await self.worker_event_dispatcher.dispatch(event_obj, self.context)
                await asyncio.sleep(0) 

        except asyncio.CancelledError: # pragma: no cover
            logger.info(f"AgentWorker '{agent_id}' async_run() loop task was cancelled.")
            if self._async_stop_event and not self._async_stop_event.is_set(): self._async_stop_event.set() 
            if self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal() and self.context.current_phase != AgentOperationalPhase.SHUTTING_DOWN:
                self.phase_manager.notify_error_occurred("Worker async_run cancelled unexpectedly.", traceback.format_exc())
        except Exception as e: # pragma: no cover
            error_details = traceback.format_exc()
            logger.error(f"Fatal error in AgentWorker '{agent_id}' async_run() loop: {e}", exc_info=True)
            if self._async_stop_event and not self._async_stop_event.is_set(): self._async_stop_event.set() 
            if self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal():
                self.phase_manager.notify_error_occurred(f"Fatal worker loop error: {str(e)}", error_details)
                if self.context.state.input_event_queues: 
                    await self.context.state.input_event_queues.enqueue_internal_system_event(
                        AgentErrorEvent(error_message=f"Fatal worker loop error: {str(e)}", exception_details=error_details)
                    )
        finally:
            logger.info(f"AgentWorker '{agent_id}' async_run() loop is exiting. Async stop event set: {self._async_stop_event.is_set() if self._async_stop_event else 'N/A'}")
            if self._async_stop_event and not self._async_stop_event.is_set() and \
               self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal(): # pragma: no cover
                logger.error(f"AgentWorker '{agent_id}': async_run loop ended prematurely without explicit async stop signal. This may indicate an issue.")
                current_error_details = traceback.format_exc() 
                self.phase_manager.notify_error_occurred("Worker async_run loop ended unexpectedly without stop signal.", current_error_details)
            
            if self.context.state.input_event_queues and hasattr(self.context.state.input_event_queues, 'log_remaining_items_at_shutdown'): # pragma: no cover
                 self.context.state.input_event_queues.log_remaining_items_at_shutdown()
            logger.info(f"AgentWorker '{agent_id}' async_run() loop has finished.")
