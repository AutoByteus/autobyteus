# file: autobyteus/llm/api/google/gemini_llm.py
from abc import ABC, abstractmethod
from autobyteus.llm.base_llm import BaseLLM
import google.generativeai as genai
import os

class GeminiLLM(BaseLLM):
    def __init__(self, model: str):
        """
        Initialize the GeminiLLM instance.

        :param model: The model to be used with Gemini.
        :type model: str
        """
        self.model = genai.GenerativeModel(model)
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    async def _send_user_message_to_llm(self, user_message, **kwargs):
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
