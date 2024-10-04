from typing import Dict, List
from autobyteus.config import config
import openai

from autobyteus.llm.api.openai.base_open_api import BaseOpenAIApi
from autobyteus.llm.api.openai.message_types import AssistantMessage, BaseMessage, MessageList, OpenAIMessageRole, SystemMessage, UserMessage
from autobyteus.llm.api.openai.models import OpenAIModel


class OpenAIChatApi(BaseOpenAIApi):
    """
    OpenAIChatApi is a concrete class that extends the BaseOpenAIApi class.
    This class processes a series of message interactions and fetches a response using the OpenAI Chat API.
    
    :param model_name: Name of the OpenAI model to be used. Defaults to OpenAIModel.GPT_3_5_TURBO or the value from the config.
    :type model_name: OpenAIModel
    """

    def __init__(self, model_name: OpenAIModel = None, system_message: str = None):
        self.initialize()
        self.model = (model_name.value if model_name 
                     else OpenAIModel(config.OPENAI_MODEL).value)
        self.system_message = system_message
        self.message_list = MessageList(system_message if system_message else None)

    @classmethod
    def initialize(cls):
        openai.api_key = config.OPENAI_API_KEY

    def send_messages(self, messages: List[BaseMessage]) -> AssistantMessage:
        """
        Process a list of message interactions and return the response using the OpenAI Chat API.

        :param messages: A list of message interactions to be processed.
        :type messages: list of BaseMessage instances
        :return: Response content from the OpenAI Chat API.
        :rtype: AssistantMessage
        """
        message_list = MessageList()
        if self.system_message:
            message_list.add_system_message(self.system_message)
        for message in messages:
            if isinstance(message, SystemMessage):
                self.message_list.add_system_message(message.content)
            elif isinstance(message, UserMessage):
                self.message_list.add_user_message(message.content)
            elif isinstance(message, AssistantMessage):
                self.message_list.add_assistant_message(message.content)

        response = openai.chat.completions.create(
            model=self.model,
            messages=self.message_list.get_messages()
        )
        # Use the _extract_response_message method to obtain the AssistantMessage instance
        return self._extract_response_message(response)


    def _extract_response_message(self, response: Dict) -> AssistantMessage:
        """
        Extract the message from the OpenAI Chat API response.

        :param response: The response from the OpenAI Chat API.
        :type response: dict
        :return: The response message.
        :rtype: AssistantMessage
        """
        try:
            message = response.choices[0].message
            if message.role != OpenAIMessageRole.ASSISTANT.value:
                raise ValueError(f"Unexpected role in OpenAI API response: {message.role}")
            return AssistantMessage(message.content)
        except (AttributeError, IndexError) as e:
            raise ValueError(f"Unexpected structure in OpenAI API response: {str(e)}")