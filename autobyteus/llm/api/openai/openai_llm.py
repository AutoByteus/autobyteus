"""
openai_llm.py: Implements the OpenAILLM class which extends the BaseLLM abstract base class.
This class integrates the OpenAI models (gpt3.5-turbo, gpt4) with the agent program. It uses the OpenAI API to process a list of 
input messages and return the model's responses.
"""

from autobyteus.llm.api.openai.base_open_api import ApiType, BaseOpenAIApi
from autobyteus.llm.api.openai.message_types import UserMessage
from autobyteus.llm.api.openai.models import OpenAIModel
from autobyteus.llm.api.openai.openai_api_factory import OpenAIApiFactory
from autobyteus.llm.base_llm import BaseLLM


class OpenAI(BaseLLM):
    """
    OpenAI is a concrete class that extends the BaseLLM class.
    This class is responsible for processing input messages and returning responses from the OpenAI GPT model.
    
    :param api_type: Type of the OpenAI API to use.
    :type api_type: ApiType
    :param model_name: Name of the OpenAI model to be used. If not provided, the default from the respective API class will be used.
    :type model_name: OpenAIModel, optional
    :param system_message: The system message to be used. If not provided, the default system message will be used.
    :type system_message: str, optional
    """

    def __init__(self, api_type: ApiType = ApiType.CHAT, model_name: OpenAIModel = None, system_message: str = None):
        super().__init__()
        if model_name:
            self.openai_api: BaseOpenAIApi = OpenAIApiFactory.create_api(api_type, model_name, system_message)
        else:
            self.openai_api: BaseOpenAIApi = OpenAIApiFactory.create_api(api_type, system_message=system_message)
        
        self.system_message = system_message
        self.history_messages = []
    
    def _send_user_message_to_llm(self, user_message, **kwargs):
        """
        Send user message to the OpenAI GPT model and return its response.

        :param user_message: The user message to be processed.
        :type user_message: str
        :return: Response content from the OpenAI GPT model.
        :rtype: str
        """
        # Convert the user message to a UserMessage
        user_message = UserMessage(user_message)
        

        
        # Process the message using the API and get the response
        assistant_message = self.openai_api.send_messages([user_message])
        self.history_messages.append[user_message]
        self.history_messages.append[assistant_message]
        return assistant_message.content

    async def cleanup(self):
        raise NotImplementedError
