from typing import Dict, List
from autobyteus.llm_integrations.openai_integration.openai_message_types import AssistantMessage, BaseMessage, OpenAIMessageRole, SystemMessage, UserMessage, MessageList
from autobyteus.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi
from autobyteus.config import config
import openai

from autobyteus.llm_integrations.openai_integration.openai_models import OpenAIModel

class OpenAIChatApi(BaseOpenAIApi):
    """
    OpenAIChatApi is a concrete class that extends the BaseOpenAIApi class.
    This class processes a series of message interactions and fetches a response using the OpenAI Chat API.
    
    :param model_name: Name of the OpenAI model to be used. Defaults to OpenAIModel.GPT_3_5_TURBO or the value from the config.
    :type model_name: OpenAIModel
    """

    def __init__(self, model_name: OpenAIModel = None):
        self.initialize()  # Ensure OpenAI is initialized
        
        # Use provided model name or default from the config
        if model_name:
            self.model = model_name.value
        else:
            model_str = config.get('OPEN_AI_MODEL', OpenAIModel.GPT_3_5_TURBO.value)
            self.model = OpenAIModel(model_str).value

    def process_input_messages(self, messages: List[BaseMessage]) -> AssistantMessage:
        """
        Process a list of message interactions and return the response using the OpenAI Chat API.

        :param messages: A list of message interactions to be processed.
        :type messages: list of BaseMessage instances
        :return: Response content from the OpenAI Chat API.
        :rtype: AssistantMessage
        """
        message_list = MessageList()
        for message in messages:
            if isinstance(message, SystemMessage):
                message_list.add_system_message(message.content)
            elif isinstance(message, UserMessage):
                message_list.add_user_message(message.content)
        
        constructed_messages = message_list.get_messages()
        
        response = openai.ChatCompletion.create(model=self.model, messages=constructed_messages)
        
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
            content = response['choices'][0]['message']['content']
            role = response['choices'][0]['message']['role']
            
            # Validate that the role is indeed "assistant"
            if role != OpenAIMessageRole.ASSISTANT.value:
                raise ValueError(f"Unexpected role in OpenAI API response: {role}")
            
            return AssistantMessage(content)
        except (KeyError, IndexError):
            raise ValueError("Unexpected structure in OpenAI API response.")
