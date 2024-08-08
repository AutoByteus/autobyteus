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

    async def send_file(self, file_path: str, **kwargs) -> str:
        """
        Send a file and return the LLM's response.

        :param file_path: The path to the file to be sent.
        :type file_path: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The LLM's response to the file content.
        :rtype: str
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        Clean up resources used by the LLM.
        This method should be called when the LLM is no longer needed.
        """
        pass