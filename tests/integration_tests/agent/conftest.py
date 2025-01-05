import pytest
import asyncio
import re
from typing import List, Optional, AsyncGenerator
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.tools.base_tool import BaseTool
from autobyteus.conversation.conversation import Conversation

class MockLLM(BaseLLM):
    def __init__(self, responses=None):
        super().__init__(model=LLMModel.MISTRAL_LARGE_API)
        self.responses = responses or ["Default response"]
        self.current_response = 0
        
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        response = self.responses[self.current_response]
        self.current_response = (self.current_response + 1) % len(self.responses)
        return response
    
    async def _stream_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[str, None]:
        response = self.responses[self.current_response]
        self.current_response = (self.current_response + 1) % len(self.responses)
        
        # Split keeping whitespace chunks intact
        chunks = re.finditer(r'\s+|\S+', response)
        for chunk in chunks:
            yield chunk.group()
            await asyncio.sleep(0.01)
        
    async def cleanup(self):
        pass

class MockTool(BaseTool):
    def __init__(self, name="mock_tool", result="mock_result"):
        super().__init__()
        self._name = name
        self._result = result
        self.execution_count = 0
        self.last_args = None
        
    def get_name(self) -> str:
        return self._name
        
    async def _execute(self, **kwargs):
        self.execution_count += 1
        self.last_args = kwargs
        return self._result
        
    def tool_usage(self) -> str:
        return f"""
        Tool: {self._name}
        Description: Mock tool for testing
        Parameters:
            - arg1 (string, required): Test argument
        """
        
    def tool_usage_xml(self) -> str:
        return f"""
        <command name="{self._name}">
            <arg name="arg1">test_value</arg>
        </command>
        """

@pytest.fixture
def mock_llm():
    return MockLLM()

@pytest.fixture
def mock_tool():
    return MockTool()

@pytest.fixture
def mock_tools(mock_tool):
    return [mock_tool]

@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()