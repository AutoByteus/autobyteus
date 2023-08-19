# tools/coordinator/operation_event_buffer.py

"""
Module for buffering operation events.

The OperationEventBuffer provides a mechanism to temporarily store recent operation events. 
This ensures that frontend services, which might miss real-time updates, can retrieve the latest events.
"""

from typing import List

class OperationEventBuffer:
    """
    Class to buffer operation events.
    
    Attributes:
        events (List[str]): A list to store recent operation events.
        max_size (int): Maximum number of events the buffer can store.
        
    Methods:
        add_event(event: str): Adds a new event to the buffer.
        get_recent_events() -> List[str]: Returns a list of recent events.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the OperationEventBuffer.
        
        Args:
            max_size (int, optional): Maximum number of events the buffer can store. 
                                      Defaults to 100.
        """
        self.events = []
        self.max_size = max_size
    
    def add_event(self, event: str) -> None:
        """
        Add a new event to the buffer.
        
        If the buffer reaches its max_size, it will remove the oldest event.
        
        Args:
            event (str): The event string to be added to the buffer.
        """
        if len(self.events) >= self.max_size:
            self.events.pop(0)
        self.events.append(event)
    
    def get_recent_events(self) -> List[str]:
        """
        Retrieve the list of recent events.
        
        Returns:
            List[str]: List of recent events stored in the buffer.
        """
        return self.events

