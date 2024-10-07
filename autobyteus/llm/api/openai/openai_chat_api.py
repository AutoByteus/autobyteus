# openai_chat_api.py
from typing import Dict, List
import openai
from dotenv import load_dotenv
import os
from enum import Enum
from autobyteus.llm.models import LLMModel
# Message Types
class OpenAIMessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class BaseMessage:
    role: OpenAIMessageRole  
    content: str
    def __init__(self, content: str):
        self.content = content
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

class SystemMessage(BaseMessage):
    role = OpenAIMessageRole.SYSTEM  

class UserMessage(BaseMessage):
    role = OpenAIMessageRole.USER  

class AssistantMessage(BaseMessage):
    role = OpenAIMessageRole.ASSISTANT  

class MessageList:
    def __init__(self, system_message: str = "You are a helpful assistant."):
        self.messages: List[BaseMessage] = []
        if system_message:
            self.add_system_message(system_message)

    def add_system_message(self, content: str):
        if content:
            self.messages = [SystemMessage(content)] + [
                msg for msg in self.messages 
                if not isinstance(msg, SystemMessage)
            ]

    def add_user_message(self, content: str):
        self.messages.append(UserMessage(content))

    def add_assistant_message(self, content: str):
        self.messages.append(AssistantMessage(content))

    def get_messages(self) -> List[Dict[str, str]]:
        return [msg.to_dict() for msg in self.messages]

# API Types
class ApiType(Enum):
    CHAT = "chat"
    COMPLETION = "completion"
# Base OpenAI API
class BaseOpenAIApi:
    def send_messages(self, messages: List[BaseMessage]) -> AssistantMessage:
        raise NotImplementedError

# OpenAI Chat API
class OpenAIChatApi(BaseOpenAIApi):
    def __init__(self, model_name: LLMModel.OpenaiApiModels = None, system_message: str = None):
        self.initialize()
        self.model = model_name.value if model_name else LLMModel.OpenaiApiModels.GPT_3_5_TURBO_API.value
        self.system_message = system_message
        self.message_list = MessageList(system_message)

    @classmethod
    def initialize(cls):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def send_messages(self, messages: List[BaseMessage]) -> AssistantMessage:
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
        return self._extract_response_message(response)

    def _extract_response_message(self, response) -> AssistantMessage:
        try:
            message = response.choices[0].message
            if message.role != OpenAIMessageRole.ASSISTANT.value:
                raise ValueError(f"Unexpected role in OpenAI API response: {message.role}")
            return AssistantMessage(message.content)
        except (AttributeError, IndexError) as e:
            raise ValueError(f"Unexpected structure in OpenAI API response: {str(e)}")

# OpenAI API Factory
class OpenAIApiFactory:
    @staticmethod
    def create_api(api_type: ApiType, model_name: LLMModel.OpenaiApiModels = None, system_message: str = None) -> BaseOpenAIApi:
        if api_type == ApiType.CHAT:
            return OpenAIChatApi(model_name, system_message)
        else:
            raise ValueError(f"Unsupported API type: {api_type}")

# OpenAI LLM Implementation
class OpenAI:
    def __init__(self, api_type: ApiType = ApiType.CHAT, model_name: LLMModel.OpenaiApiModels = None, system_message: str = None):
        if model_name:
            self.openai_api: BaseOpenAIApi = OpenAIApiFactory.create_api(api_type, model_name, system_message)
        else:
            self.openai_api = OpenAIApiFactory.create_api(api_type, system_message=system_message)
        self.system_message = system_message
        self.history_messages = []

    def send_message(self, user_message: str, **kwargs) -> str:
        user_message = UserMessage(user_message)
        assistant_message = self.openai_api.send_messages([user_message])
        self.history_messages.append(user_message)
        self.history_messages.append(assistant_message)
        return assistant_message.content

    async def cleanup(self):
        # Implement cleanup logic if needed
        pass