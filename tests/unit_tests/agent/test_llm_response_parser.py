import pytest
from autobyteus.agent.response_parser.llm_response_parser import LLMResponseParser

@pytest.fixture
def response_parser():
    return LLMResponseParser()

def test_parse_response_with_tool_invocation(response_parser):
    response = """
    I am currently analyzing the task and preparing to search for an encouraging movie for students. To begin this process, I'll need to use the Google Search tool to find relevant information.

    Reason: To find an appropriate movie that is encouraging for students, I need to search for recommendations or lists of inspiring films targeted at this audience.

    Act: <<<GoogleSearch(query="best encouraging movies for students")>>>

    I will stop here now and wait for the GoogleSearch tool to return the results...
    """

    parsed_response = response_parser.parse_response(response)

    assert parsed_response.is_tool_invocation() == True
    assert parsed_response.tool_name == "GoogleSearch"
    assert parsed_response.tool_args == {"query": "best encouraging movies for students"}

def test_parse_response_without_tool_invocation(response_parser):
    response = """
    Based on the search results, here are some encouraging movies for students:

    1. "Dead Poets Society" (1989) - This film follows an English teacher who inspires his students to pursue their dreams and think for themselves.

    2. "Freedom Writers" (2007) - Based on a true story, this movie depicts a young teacher who helps a group of at-risk students find their voices through writing.

    3. "October Sky" (1999) - Set in a coal mining town, this film tells the story of a high school student who pursues his passion for rocketry despite the odds.

    These movies showcase the power of education, perseverance, and following one's dreams, making them excellent choices for inspiring and encouraging students.
    """

    parsed_response = response_parser.parse_response(response)

    assert parsed_response.is_tool_invocation() == False
    assert parsed_response.tool_name is None
    assert parsed_response.tool_args is None