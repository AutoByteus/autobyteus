# File: tests/integration_tests/llm_integrations/openai_integration/test_openai_chat_api_integration.py

from openai import InvalidRequestError
import pytest
from src.llm_integrations.openai_integration.openai_chat_api import OpenAIChatApi

@pytest.mark.skip(reason="Integration test calling the real OpenAI API")
def test_process_input_messages_integration():
    """Integration test to check if the process_input_messages method interacts correctly with the OpenAI Chat API."""
    api = OpenAIChatApi()
    messages = [{"role": "user", "content": "Hello, OpenAI!"}]
    response = api.process_input_messages(messages)
    assert isinstance(response, str)  # The response should be a string

@pytest.mark.skip(reason="Integration test calling the real OpenAI API")
def test_process_input_messages_with_empty_messages_integration():
    """Integration test to check the process_input_messages method with an empty list of messages."""
    api = OpenAIChatApi()
    messages = []
    with pytest.raises(InvalidRequestError, match=r".*too short - 'messages'.*"):
        api.process_input_messages(messages)

@pytest.mark.skip(reason="Integration test calling the real OpenAI API")
def test_refine_writing_integration():
    """Integration test to check if the process_input_messages method interacts correctly with the OpenAI Chat API for refining writing tasks."""
    api = OpenAIChatApi()
    
    # Using the provided prompt as the message content
    messages = [
        {
            "role": "system",
            "content": "You are ChatGPT, a large language model trained by OpenAI, based on the GPT-3.5 architecture. Knowledge cutoff: September 2021. Please feel free to ask me anything."
        },
        {
            "role": "user",
            "content": """
            As an expert in refining writting, your task is to improve the given writting situated within the [Writting] section. The content of the writting is situated within the $start$ and $end$ tokens.

            Follow the steps below, each accompanied by a title and a description:
            1. Analyze the Prompt:
               - Dissect the prompt to understand its content and objectives.
            2. Determine the Domain:
               - Identify the domain to which this prompt belongs.
            3. Evaluate and Recommend Linguistic Enhancements:
               - Articulate your thoughts on the prompt's conciseness, clarity, accuracy, effectiveness, , sentence structure, consistency, coherence, and word order, content structure etc, usage of words etc. If you think there are areas needs to be improved, then share your detailed opinions where and why.
            4. Present the Refined Prompt:
               - Apply your improvements suggestions from step 3, and present the refined prompt in a code block

            [Writting]
            $start$
            As a top Vue3 frontend engineer, your task is to analyze the error and relevant codes, and based on your analysis results either propose a solution or add more debugging information for further analysis.
            ... (rest of the content)
            $end$
            """
        }
    ]
    
    response = api.process_input_messages(messages)
    print(response)
    assert isinstance(response, str)  # The response should be a string
    # Additional assertions can be added based on expected outputs or response characteristics

