from abc import ABC, abstractmethod

class BaseLLM(ABC):
    """
    BaseLLM is an abstract base class that defines the common interface for all LLM integrations.
    """

    def initialize(self):
        """
        Initialize the BaseLLM object.
        """
        pass

    @abstractmethod
    def send_user_message(self, user_message, **kwargs):
        """
        send a user message and return the LLM's response.

        :param user_message: The user message to be processed.
        :type user_message: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        Clean up resources used by the LLM.
        This method should be called when the LLM is no longer needed.
        """
        pass