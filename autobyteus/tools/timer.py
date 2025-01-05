import asyncio
from typing import Optional
from autobyteus.tools.base_tool import BaseTool
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

class Timer(BaseTool, EventEmitter):
    """
    A tool that provides timer functionality with configurable duration and event emission.

    This class inherits from BaseTool and EventEmitter. It allows setting a timer duration,
    starting the timer, and emits events with the remaining time at configurable intervals.
    The timer runs independently after being started.

    Attributes:
        duration (int): The duration of the timer in seconds.
        interval (int): The interval at which to emit timer events, in seconds.
        _is_running (bool): Flag to indicate if the timer is currently running.
        _task (Optional[asyncio.Task]): The asyncio task for the running timer.
    """

    def __init__(self):
        """
        Initialize the Timer.
        """
        BaseTool.__init__(self)
        EventEmitter.__init__(self)
        self.duration: int = 0
        self.interval: int = 60  # Default to 60 seconds if not specified
        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None

    def set_duration(self, duration: int):
        """
        Set the duration of the timer.

        Args:
            duration (int): The duration of the timer in seconds.
        """
        self.duration = duration

    def set_interval(self, interval: int):
        """
        Set the interval for emitting timer events.

        Args:
            interval (int): The interval at which to emit timer events, in seconds.
        """
        self.interval = interval

    def start(self):
        """
        Start the timer if it's not already running.

        Raises:
            RuntimeError: If the timer is already running or if no duration has been set.
        """
        if self._is_running:
            raise RuntimeError("Timer is already running")
        if self.duration <= 0:
            raise RuntimeError("Timer duration must be set before starting")
        self._is_running = True
        self._task = asyncio.create_task(self._run_timer())

    async def _run_timer(self):
        """
        Run the timer, emitting events at the specified interval.
        """
        remaining_time = self.duration
        while remaining_time > 0:
            self.emit(EventType.TIMER_UPDATE, remaining_time=remaining_time)
            await asyncio.sleep(min(self.interval, remaining_time))
            remaining_time -= self.interval
        self.emit(EventType.TIMER_UPDATE, remaining_time=0)
        self._is_running = False

    async def _execute(self, **kwargs):
        """
        Execute the timer.

        This method sets the duration and interval if provided, and starts the timer.
        It returns immediately after starting the timer, allowing the timer to run independently.

        Args:
            **kwargs: Keyword arguments. Expected arguments:
                - duration (int): The duration to set for the timer in seconds.
                - interval (int, optional): The interval at which to emit timer events, in seconds.
                  Defaults to 60 seconds if not provided.

        Returns:
            str: A message indicating the timer has started.

        Raises:
            ValueError: If the duration is not provided.
        """
        duration = kwargs.get('duration')
        if duration is None:
            raise ValueError("Timer duration must be provided")
        self.set_duration(duration)
        
        interval = kwargs.get('interval', 60)
        self.set_interval(interval)

        self.start()
        return f"Timer started for {self.duration} seconds, emitting events every {self.interval} seconds"

    def tool_usage(self):
        """
        Return a string describing the usage of the Timer.
        """
        return 'Timer: Sets and runs a timer, emitting events with remaining time. Usage: <<<Timer(duration=300, interval=60)>>>, where duration and interval are in seconds.'

    def tool_usage_xml(self):
        """
        Return an XML string describing the usage of the Timer.
        """
        return '''Timer: Sets and runs a timer, emitting events with remaining time. Usage:
    <command name="Timer">
        <arg name="duration">300</arg>
        <arg name="interval" optional="true">60</arg>
    </command>
    where duration and interval are in seconds. interval is optional and defaults to 60 seconds.
    '''