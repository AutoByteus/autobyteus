
import pytest
from autobyteus.llm.token_counter.openai_token_counter import OpenAITokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message, MessageRole

@pytest.fixture
def openai_token_counter():
    return OpenAITokenCounter(LLMModel.CHATGPT_4O_LATEST_API)

@pytest.fixture
def system_message():
    return Message(
        role=MessageRole.SYSTEM,
        content="You are a knowledgeable assistant proficient in various topics. Provide clear and concise answers."
    )

@pytest.fixture
def user_message_initial():
    return Message(role=MessageRole.USER, content="Can you explain the concept of recursion in programming?")

@pytest.fixture
def assistant_message_first():
    return Message(
        role=MessageRole.ASSISTANT, 
        content="""Certainly! Recursion is a programming technique where a function calls itself in order to solve smaller instances of the same problem. It typically involves a base case to terminate the recursive calls and a recursive case where the function continues to call itself with modified parameters.

For example, here's a simple recursive function to calculate the factorial of a number:

```python
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)
```

Would you like a more detailed explanation or another example?"""
    )

@pytest.fixture
def user_message_followup():
    return Message(
        role=MessageRole.USER,
        content="Yes, please provide another example using recursion to traverse a binary tree."
    )

@pytest.fixture
def assistant_message_second():
    return Message(
        role=MessageRole.ASSISTANT,
        content="""Sure! Traversing a binary tree using recursion can be done in several ways, such as in-order, pre-order, or post-order traversal. Here's an example of in-order traversal:

```python
class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def in_order_traversal(node):
    if node:
        in_order_traversal(node.left)
        print(node.value)
        in_order_traversal(node.right)
```

In this example, the `in_order_traversal` function recursively visits the left subtree, processes the current node, and then visits the right subtree. This results in the nodes being printed in ascending order if the binary tree is a binary search tree.

Do you need further details or assistance with another type of traversal?"""
    )

@pytest.fixture
def user_message_final():
    return Message(
        role=MessageRole.USER,
        content="No, that's all for now. Thank you!"
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

def test_count_input_tokens_empty_list(openai_token_counter):
    assert openai_token_counter.count_input_tokens([]) == 0

def test_count_output_tokens_empty_message(openai_token_counter):
    empty_message = Message(role=MessageRole.ASSISTANT, content="")
    assert openai_token_counter.count_output_tokens(empty_message) == 0

def test_count_input_tokens_complex_conversation(openai_token_counter, complex_conversation):
    token_count = openai_token_counter.count_input_tokens(complex_conversation)
    assert token_count > 0
    simple_message = [Message(role=MessageRole.USER, content="Hello")]
    simple_count = openai_token_counter.count_input_tokens(simple_message)
    assert token_count > simple_count * 6  # Updated multiplier to account for system message

def test_count_input_tokens_partial_conversation(openai_token_counter, complex_conversation):
    partial_conversation = complex_conversation[:2]  # Now includes system and first user message
    partial_count = openai_token_counter.count_input_tokens(partial_conversation)
    
    full_count = openai_token_counter.count_input_tokens(complex_conversation)
    
    assert partial_count > 0
    assert full_count > partial_count

def test_count_tokens_large_conversation(openai_token_counter):
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
    
    token_count = openai_token_counter.count_input_tokens(large_conversation)
    assert token_count > 0

def test_mixed_message_types(openai_token_counter):
    mixed_conversation = [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello!"),
        Message(role=MessageRole.ASSISTANT, content="Hi! How can I assist you today?"),
        Message(role=MessageRole.USER, content="Can you help me with my homework?"),
        Message(role=MessageRole.ASSISTANT, content="Of course! What subject are you working on?"),
        Message(role=MessageRole.USER, content="I'm studying biology.")
    ]
    
    token_count = openai_token_counter.count_input_tokens(mixed_conversation)
    assert token_count > 0
