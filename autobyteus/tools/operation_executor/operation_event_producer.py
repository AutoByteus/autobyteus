#code_start#

# File path: tools/operation_executor/operation_event_producer.py

from autobyteus.tools.operation_executor.operation_event_buffer import OperationEventBuffer


class OperationEventProducer:
    """
    Class responsible for emitting real-time events for every operation executed or undone.
    """
    
    def __init__(self, event_buffer: OperationEventBuffer):
        """
        Initializes the OperationEventProducer with the OperationEventBuffer.
        
        Args:
            event_buffer (OperationEventBuffer): The buffer where events will be stored.
        """
        self.event_buffer = event_buffer

    def emit_event(self, event: str):
        """
        Emit a real-time event for an operation.
        
        Args:
            event (str): Event to be emitted.
        """
        self.event_buffer.add_event(event)