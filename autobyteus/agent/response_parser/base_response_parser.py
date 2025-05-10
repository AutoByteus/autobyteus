from abc import ABC, abstractmethod
from autobyteus.events.event_emitter import EventEmitter

class BaseResponseParser(ABC, EventEmitter):
    """
    Base interface for response parsers.
    
    Response parsers are responsible for parsing LLM responses and emitting
    events to trigger appropriate actions in the agent.
    """
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    async def parse_response(self, response: str) -> None:
        """
        Parse the response and emit appropriate events.
        
        Args:
            response: The LLM response string to parse
        """
        pass
