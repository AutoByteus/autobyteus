import pytest
from typing import List, Tuple
from autobyteus.conversation.conversation import Conversation
from autobyteus.llm.base_llm import BaseLLM

class MockStreamingLLM(BaseLLM):
    def __init__(self):
        super().__init__(model="mock")
        self.messages = []

    async def _send_user_message_to_llm(self, user_message: str, file_paths: List[str] = None, **kwargs) -> str:
        return "Mock response"

    async def _stream_user_message_to_llm(self, user_message: str, file_paths: List[str] = None, **kwargs):
        tokens = ["Hello", " world", "!"]
        for token in tokens:
            yield token

@pytest.fixture
def conversation():
    return Conversation(MockStreamingLLM())

@pytest.mark.asyncio
async def test_stream_user_message(conversation):
    user_input = "Test message"
    received_tokens = []
    complete_response = ""
    
    async for token in conversation.stream_user_message(user_input):
        print(f"Received token: {token}")
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token
    
    # Verify tokens were received
    assert len(received_tokens) > 0
    assert complete_response == "Hello world!"
    
    # Verify conversation history
    history = conversation.get_conversation_history()
    assert len(history) == 2
    assert history[0] == ("user", user_input)
    assert history[1] == ("assistant", complete_response)

@pytest.mark.asyncio
async def test_stream_user_message_with_files(conversation):
    user_input = "Test message"
    file_paths = ["test.py", "config.json"]
    complete_response = ""
    
    async for token in conversation.stream_user_message(user_input, file_paths):
        print(f"Received token: {token}")
        complete_response += token
    
    print(f"\nComplete response: {complete_response}")
    
    history = conversation.get_conversation_history()
    expected_user_message = f"Test message\n[Files sent: {', '.join(file_paths)}]"
    assert history[0] == ("user", expected_user_message)