import asyncio
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from autobyteus.events.event_emitter import EventEmitter 
from autobyteus.events.event_types import EventType
import logging 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class Timer(BaseTool, EventEmitter): 
    """
    A tool that provides timer functionality with configurable duration and event emission.
    The timer runs independently after being started and emits TIMER_UPDATE events.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self, config=config)
        EventEmitter.__init__(self) 
        
        self.duration: int = 300  
        self.interval: int = 60   
        
        if config:
            try:
                self.duration = int(config.get('duration', 300))
                if not (1 <= self.duration <= 86400): 
                    logger.warning(f"Timer duration {self.duration} out of bounds (1-86400). Clamping or using default.")
                    self.duration = max(1, min(self.duration, 86400)) 
            except ValueError:
                logger.warning(f"Invalid duration value in config, using default {self.duration}s.")
            
            try:
                self.interval = int(config.get('interval', 60))
                if not (1 <= self.interval <= 3600): 
                    logger.warning(f"Timer interval {self.interval} out of bounds (1-3600). Clamping or using default.")
                    self.interval = max(1, min(self.interval, 3600)) 
            except ValueError:
                 logger.warning(f"Invalid interval value in config, using default {self.interval}s.")

        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        logger.debug(f"Timer initialized with duration: {self.duration}s, interval: {self.interval}s")

    @classmethod
    def get_description(cls) -> str:
        return "Sets and runs a timer. Emits TIMER_UPDATE events with remaining time at specified intervals."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="duration",
            param_type=ParameterType.INTEGER,
            description="Duration to set for this timer run in seconds.",
            required=True, 
            min_value=1,
            max_value=86400
        ))
        schema.add_parameter(ParameterDefinition(
            name="interval",
            param_type=ParameterType.INTEGER,
            description="Interval for emitting timer events in seconds for this run. Overrides instance default.",
            required=False, 
            default_value=None, 
            min_value=1,
            max_value=3600
        ))
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: 
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="duration",
            param_type=ParameterType.INTEGER,
            description="Default duration of the timer in seconds if not overridden by execute.",
            required=False,
            default_value=300,
            min_value=1,
            max_value=86400 
        ))
        schema.add_parameter(ParameterDefinition(
            name="interval",
            param_type=ParameterType.INTEGER,
            description="Default interval at which to emit timer events, in seconds, if not overridden by execute.",
            required=False,
            default_value=60,
            min_value=1,
            max_value=3600
        ))
        return schema

    def set_duration(self, duration: int) -> None: 
        if not (1 <= duration <= 86400):
            raise ValueError("Duration must be between 1 and 86400 seconds.")
        self.duration = duration

    def set_interval(self, interval: int) -> None: 
        if not (1 <= interval <= 3600):
            raise ValueError("Interval must be between 1 and 3600 seconds.")
        self.interval = interval

    def start(self, run_duration: Optional[int] = None, run_interval: Optional[int] = None) -> None: 
        if self._is_running:
            logger.warning("Timer start called but timer is already running.")
            return

        current_duration = run_duration if run_duration is not None else self.duration
        current_interval = run_interval if run_interval is not None else self.interval
        
        if current_duration <= 0:
            raise RuntimeError("Timer duration must be positive and set before starting.")
        if current_interval <=0:
            raise RuntimeError("Timer interval must be positive and set.")

        self._is_running = True
        self._task = asyncio.create_task(self._run_timer_task(current_duration, current_interval))
        logger.info(f"Timer started for {current_duration}s, events every {current_interval}s.")

    async def _run_timer_task(self, duration: int, interval: int) -> None: 
        remaining_time = duration
        try:
            while remaining_time > 0:
                self.emit(EventType.TIMER_UPDATE, remaining_time=remaining_time)
                await asyncio.sleep(min(interval, remaining_time))
                remaining_time -= interval
            self.emit(EventType.TIMER_UPDATE, remaining_time=0) 
        except asyncio.CancelledError:
            logger.info("Timer task was cancelled.")
            self.emit(EventType.TIMER_UPDATE, remaining_time=-1, status="cancelled") 
            raise 
        finally:
            self._is_running = False
            logger.info("Timer task finished.")

    async def _execute(self, context: 'AgentContext', duration: int, interval: Optional[int] = None) -> str: 
        logger.debug(f"Timer execute called by agent {context.agent_id} with duration: {duration}, interval: {interval}")
        
        effective_interval = interval if interval is not None else self.interval

        if self._task and not self._task.done():
            logger.info("Cancelling previous timer task before starting a new one.")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.debug("Previous timer task successfully cancelled.")
            self._task = None 

        self.start(run_duration=duration, run_interval=effective_interval) 
        return f"Timer started for {duration} seconds, emitting events every {effective_interval} seconds."

    async def stop(self) -> None: 
        if self._task and not self._task.done():
            logger.info("Stopping timer task...")
            self._task.cancel()
            try:
                await self._task 
            except asyncio.CancelledError:
                logger.info("Timer task stopped successfully.")
            self._task = None
            self._is_running = False 
        else:
            logger.info("Stop called, but no timer task is running or task already done.")
