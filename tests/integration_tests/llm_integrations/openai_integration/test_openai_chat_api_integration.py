from openai import InvalidRequestError
import pytest
from src.llm_integrations.openai_integration.openai_chat_api import OpenAIChatApi
from src.llm_integrations.openai_integration.openai_message_types import UserMessage, SystemMessage, AssistantMessage

@pytest.mark.skip(reason="Integration test calling the real OpenAI API")
def test_process_input_messages_integration():
    """
    Integration test to check if the process_input_messages method interacts correctly with the OpenAI Chat API.
    """
    api = OpenAIChatApi()
    messages = [UserMessage("Hello, OpenAI!")]
    response = api.process_input_messages(messages)
    assert isinstance(response, AssistantMessage)  # Ensure response is an AssistantMessage instance
    assert isinstance(response.content, str)  # The content of the response should be a string

@pytest.mark.skip(reason="Integration test calling the real OpenAI API")
def test_refine_writing_integration():
    """
    Integration test to check if the process_input_messages method interacts correctly with the OpenAI Chat API for refining writing tasks.
    """
    api = OpenAIChatApi()
    
    system_message = SystemMessage("You are ChatGPT, a large language model trained by OpenAI, based on the GPT-3.5 architecture. Knowledge cutoff: September 2021. Please feel free to ask me anything.")
    user_message_content = """
    As an expert in refining writing, your task is to improve the given writing situated within the [Writing] section. The content of the writing is situated within the $start$ and $end$ tokens.

    Follow the steps below, each accompanied by a title and a description:
    1. Analyze the Prompt:
       - Dissect the prompt to understand its content and objectives.
    2. Determine the Domain:
       - Identify the domain to which this prompt belongs.
    3. Evaluate and Recommend Linguistic Enhancements:
       - Articulate your thoughts on the prompt's conciseness, clarity, accuracy, effectiveness, sentence structure, consistency, coherence, word order, content structure, usage of words, etc. If you think there are areas that need to be improved, then share your detailed opinions where and why.
    4. Present the Refined Prompt:
       - Apply your improvement suggestions from step 3 and present the refined prompt in a code block.

    [Writing]
    $start$
    As a top Vue3 frontend engineer, your task is to analyze the error and relevant codes, and based on your analysis results either propose a solution or add more debugging information for further analysis.
    ... (rest of the content)
    $end$
    """
    user_message = UserMessage(user_message_content)
    
    messages = [system_message, user_message]
    response = api.process_input_messages(messages)
    assert isinstance(response, AssistantMessage)  # Ensure response is an AssistantMessage instance
    assert isinstance(response.content, str)  # The content of the response should be a string


