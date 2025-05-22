import asyncio
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from autobyteus.events.event_emitter import EventEmitter # Timer uses its own event emission
from autobyteus.events.event_types import EventType
import logging # Added logging

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__) # Initialize logger

class Timer(BaseTool): # Removed EventEmitter from inheritance as BaseTool already inherits it.
    """
    A tool that provides timer functionality with configurable duration and event emission.

    This class inherits from BaseTool. It allows setting a timer duration,
    starting the timer, and emits events with the remaining time at configurable intervals.
    The timer runs independently after being started.

    Attributes:
        duration (int): The duration of the timer in seconds.
        interval (int): The interval at which to emit timer events, in seconds.
        _is_running (bool): Flag to indicate if the timer is currently running.
        _task (Optional[asyncio.Task]): The asyncio task for the running timer.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        """
        Initialize the Timer.
        """
        super().__init__() # Calls BaseTool.__init__ which calls EventEmitter.__init__
        
        # Extract configuration with defaults
        self.duration: int = 300  # Default 5 minutes
        self.interval: int = 60   # Default 60 seconds
        
        if config:
            configured_duration = config.get('duration', 300)
            if isinstance(configured_duration, int):
                self.duration = configured_duration
            else:
                logger.warning(f"Invalid type for 'duration' in Timer config: {type(configured_duration)}. Using default {self.duration}.")

            configured_interval = config.get('interval', 60)
            if isinstance(configured_interval, int):
                self.interval = configured_interval
            else:
                logger.warning(f"Invalid type for 'interval' in Timer config: {type(configured_interval)}. Using default {self.interval}.")

        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        logger.debug(f"Timer tool initialized. Duration: {self.duration}s, Interval: {self.interval}s")


    @classmethod
    def get_config_schema(cls) -> 'ToolConfigSchema':
        """
        Return the configuration schema for this tool.
        
        Returns:
            ToolConfigSchema: Schema describing the tool's configuration parameters.
        """
        schema = ToolConfigSchema()
        
        schema.add_parameter(ToolConfigParameter(
            name="duration",
            param_type=ParameterType.INTEGER,
            description="Duration of the timer in seconds.",
            required=False, # If not provided in config, __init__ uses its default.
            default_value=300,
            min_value=1,
            max_value=86400  # Max 24 hours
        ))
        
        schema.add_parameter(ToolConfigParameter(
            name="interval",
            param_type=ParameterType.INTEGER,
            description="Interval at which to emit timer events, in seconds.",
            required=False, # If not provided in config, __init__ uses its default.
            default_value=60,
            min_value=1,
            max_value=3600  # Max 1 hour
        ))
        
        return schema

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the Timer tool.

        Returns:
            str: An XML description of how to use the Timer tool.
        """
        return '''Timer: Sets and runs a timer, emitting events with remaining time. Usage:
    <command name="Timer">
        <arg name="duration">300</arg> <!-- Duration in seconds -->
        <arg name="interval" optional="true">60</arg> <!-- Interval in seconds, defaults to 60 if not provided -->
    </command>
    The timer runs in the background. This command starts it.
    '''

    def _set_duration(self, duration: int): # Renamed to avoid conflict with property if any
        """
        Set the duration of the timer.
        Args:
            duration (int): The duration of the timer in seconds.
        """
        if not isinstance(duration, int) or duration <= 0:
            raise ValueError("Timer duration must be a positive integer.")
        self.duration = duration

    def _set_interval(self, interval: int): # Renamed
        """
        Set the interval for emitting timer events.
        Args:
            interval (int): The interval, in seconds.
        """
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("Timer interval must be a positive integer.")
        self.interval = interval

    def _start_timer_instance(self, agent_id_for_event: str): # Renamed, added agent_id
        """
        Start the timer if it's not already running.
        Args:
            agent_id_for_event: The agent_id to include in emitted timer events.
        Raises:
            RuntimeError: If the timer is already running or if no duration has been set.
        """
        if self._is_running:
            logger.warning(f"Timer for agent '{agent_id_for_event}' is already running. Start request ignored.")
            raise RuntimeError("Timer is already running")
        if self.duration <= 0: # Should be caught by _set_duration
            logger.error(f"Timer duration for agent '{agent_id_for_event}' is not set or invalid ({self.duration}s). Cannot start.")
            raise RuntimeError("Timer duration must be set to a positive value before starting")
        
        self._is_running = True
        # Pass agent_id to _run_timer for inclusion in events
        self._task = asyncio.create_task(self._run_timer_logic(agent_id_for_event), name=f"timer_task_agent_{agent_id_for_event}")
        logger.info(f"Timer task created for agent '{agent_id_for_event}'. Duration: {self.duration}s, Interval: {self.interval}s.")


    async def _run_timer_logic(self, agent_id_for_event: str): # Renamed, added agent_id
        """
        Run the timer, emitting events at the specified interval.
        Args:
            agent_id_for_event: The agent_id to use in emitted events.
        """
        try:
            remaining_time = self.duration
            logger.debug(f"Timer loop starting for agent '{agent_id_for_event}'. Initial remaining time: {remaining_time}s.")
            while remaining_time > 0 and self._is_running: # Check _is_running for potential external stop
                # Emit event with agent_id
                self.emit(EventType.TIMER_UPDATE, agent_id=agent_id_for_event, remaining_time=remaining_time)
                logger.debug(f"Timer for agent '{agent_id_for_event}': Emitted TIMER_UPDATE. Remaining: {remaining_time}s.")
                
                sleep_duration = min(self.interval, remaining_time)
                await asyncio.sleep(sleep_duration)
                remaining_time -= self.interval # Or remaining_time -= sleep_duration for more accuracy
            
            if self._is_running: # If loop finished naturally
                self.emit(EventType.TIMER_UPDATE, agent_id=agent_id_for_event, remaining_time=0) # Final update
                logger.info(f"Timer for agent '{agent_id_for_event}' completed.")
        except asyncio.CancelledError:
            logger.info(f"Timer task for agent '{agent_id_for_event}' was cancelled.")
        except Exception as e: # pragma: no cover
            logger.error(f"Error in timer loop for agent '{agent_id_for_event}': {e}", exc_info=True)
        finally:
            self._is_running = False
            logger.debug(f"Timer loop finished for agent '{agent_id_for_event}'. Is running: {self._is_running}.")


    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Execute the timer. Sets duration/interval from kwargs and starts the timer.
        The timer runs independently in the background.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Keyword arguments. Expected:
                - duration (int): The duration for the timer in seconds.
                - interval (int, optional): Interval for timer events, in seconds. Defaults to tool's configured interval.

        Returns:
            str: A message indicating the timer has started.
        """
        duration_arg = kwargs.get('duration')
        if duration_arg is None:
            raise ValueError("Timer 'duration' (in seconds) must be provided in arguments.")
        
        try:
            # Prioritize args from LLM call, then tool config, then class defaults.
            # Here, LLM args override existing settings for this execution.
            exec_duration = int(duration_arg)
            self._set_duration(exec_duration) # Validate and set
        except ValueError as e:
            raise ValueError(f"Invalid 'duration' argument: {e}")

        interval_arg = kwargs.get('interval')
        if interval_arg is not None:
            try:
                exec_interval = int(interval_arg)
                self._set_interval(exec_interval) # Validate and set
            except ValueError as e:
                raise ValueError(f"Invalid 'interval' argument: {e}")
        # If interval_arg is None, self.interval (from config or class default) is used.

        agent_id_for_timer_events = context.agent_id # Use agent_id from context for emitted events

        if self._is_running: # If a timer task from this instance is already active
            logger.warning(f"Timer for agent '{agent_id_for_timer_events}' is already running. It will be reset with new parameters.")
            if self._task and not self._task.done():
                self._task.cancel() # Cancel existing timer task
            self._is_running = False # Ensure flag is reset

        self._start_timer_instance(agent_id_for_timer_events)
        
        return_message = (
            f"Timer started for agent '{agent_id_for_timer_events}'. "
            f"Duration: {self.duration} seconds. "
            f"Event interval: {self.interval} seconds. "
            "Timer runs in the background."
        )
        logger.info(return_message)
        return return_message

    # Optional: Add a method to stop the timer if needed by other logic
    async def stop_timer(self): # pragma: no cover
        """Stops the currently running timer task, if any."""
        if self._is_running and self._task:
            logger.info(f"Stopping timer for agent '{self.agent_id}'.")
            self._is_running = False # Signal loop to stop
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.debug(f"Timer task for agent '{self.agent_id}' successfully cancelled.")
            self._task = None
        else:
            logger.debug(f"Stop timer called for agent '{self.agent_id}', but no timer is running or task found.")
