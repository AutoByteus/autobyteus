
import pytest
from autobyteus.llm.token_counter.mistral_token_counter import MistralTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message, MessageRole

@pytest.fixture
def mistral_token_counter():
    return MistralTokenCounter(LLMModel["mistral-large"])

@pytest.fixture
def system_message():
    return Message(
        role=MessageRole.SYSTEM,
        content="You are a helpful programming tutor specializing in data structures and algorithms. Provide clear, step-by-step explanations and ensure code examples follow Python best practices."
    )

@pytest.fixture
def user_message_initial():
    return Message(role=MessageRole.USER, content="Can you help me understand how to implement a binary search tree in Python?")

@pytest.fixture
def assistant_message_first():
    return Message(
        role=MessageRole.ASSISTANT, 
        content="""I'll help you implement a binary search tree. First, let's start with the basic node structure:

class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

Would you like me to explain how to implement the insertion method next?"""
    )

@pytest.fixture
def user_message_followup():
    return Message(
        role=MessageRole.USER,
        content="Yes, please explain the insertion method. Also, how would we handle duplicate values?"
    )

@pytest.fixture
def assistant_message_second():
    return Message(
        role=MessageRole.ASSISTANT,
        content="""The insertion method recursively finds the correct position for a new value. Here's how we can implement it:

def insert(self, value):
    if value < self.value:
        if self.left is None:
            self.left = Node(value)
        else:
            self.left.insert(value)
    elif value > self.value:
        if self.right is None:
            self.right = Node(value)
        else:
            self.right.insert(value)
            
For duplicates, we have several options:
1. Reject duplicates
2. Keep a count in each node
3. Add to either left or right consistently

Which approach would you prefer to implement?"""
    )

@pytest.fixture
def user_message_final():
    return Message(
        role=MessageRole.USER,
        content="Let's implement the option to reject duplicates."
    )

@pytest.fixture
def complex_conversation(system_message, user_message_initial, assistant_message_first, 
                        user_message_followup, assistant_message_second,
                        user_message_final):
    return [
        system_message,
        user_message_initial,
        assistant_message_first,
        user_message_followup,
        assistant_message_second,
        user_message_final
    ]

def test_count_input_tokens_empty_list(mistral_token_counter):
    assert mistral_token_counter.count_input_tokens([]) == 0

def test_count_output_tokens_empty_message(mistral_token_counter):
    empty_message = Message(role=MessageRole.ASSISTANT, content="")
    assert mistral_token_counter.count_output_tokens(empty_message) == 0

def test_count_input_tokens_complex_conversation(mistral_token_counter, complex_conversation):
    token_count = mistral_token_counter.count_input_tokens(complex_conversation)
    assert token_count > 0
    simple_message = [Message(role=MessageRole.USER, content="Hello")]
    simple_count = mistral_token_counter.count_input_tokens(simple_message)
    assert token_count > simple_count * 6  # Updated multiplier to account for system message

def test_count_input_tokens_partial_conversation(mistral_token_counter, complex_conversation):
    partial_conversation = complex_conversation[:2]  # Now includes system and first user message
    partial_count = mistral_token_counter.count_input_tokens(partial_conversation)
    
    full_count = mistral_token_counter.count_input_tokens(complex_conversation)
    
    assert partial_count > 0
    assert full_count > partial_count

def test_count_tokens_large_conversation(mistral_token_counter):
    large_conversation = [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant.")
    ]
    base_message = "This is message number"
    
    # Create pairs after system message
    for i in range(10):
        large_conversation.extend([
            Message(role=MessageRole.USER, content=f"{base_message} {i*2+1}"),
            Message(role=MessageRole.ASSISTANT, content=f"{base_message} {i*2+2}")
        ])
    # Add final user message
    large_conversation.append(Message(role=MessageRole.USER, content="Final message"))
    
    token_count = mistral_token_counter.count_input_tokens(large_conversation)
    assert token_count > 0


def test_mixed_message_types(mistral_token_counter):
    mixed_conversation = [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello!"),
        Message(role=MessageRole.ASSISTANT, content="Hi! How can I help?"),
        Message(role=MessageRole.USER, content="What's the weather?"),
        Message(role=MessageRole.ASSISTANT, content="I don't have access to current weather data."),
        Message(role=MessageRole.USER, content="Thanks for letting me know!")
    ]
    
    token_count = mistral_token_counter.count_input_tokens(mixed_conversation)
    assert token_count > 0
    
