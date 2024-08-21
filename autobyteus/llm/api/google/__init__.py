from abc import ABC, abstractmethod
import google.generativeai as genai
import os

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
        Send a user message and return the LLM's response.

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

class GeminiLLM(BaseLLM):
    def __init__(self, model: str):
        """
        Initialize the GeminiLLM instance.

        :param model: The model to be used with Gemini.
        :type model: str
        """
        self.model = genai.GenerativeModel(model)
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    async def send_user_message(self, user_message, **kwargs):
        """
        Send a user message and return the LLM's response.

        :param user_message: The user message to be processed.
        :type user_message: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The LLM's response to the user message.
        :rtype: str
        """
        response = self.model.generate_content(user_message)
        return response.text

    async def cleanup(self):
        """
        Clean up resources used by the Gemini LLM.
        """
        # No specific cleanup required for the Gemini client library
        pass
