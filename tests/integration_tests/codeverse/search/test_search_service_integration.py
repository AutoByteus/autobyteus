# File Path: tests/integration_tests/semantic_code/search/test_search_service_integration.py

"""
tests/integration_tests/semantic_code/search/test_search_service_integration.py

Integration tests for the SearchService class to ensure that it correctly searches for code entities.
"""

import tempfile
import textwrap
from typing import List
import pytest
from autobyteus.codeverse.search.search_service import SearchService
from autobyteus.codeverse.core.code_entities.function_entity import FunctionEntity
from autobyteus.codeverse.index.index_service import IndexService
from autobyteus.codeverse.core.code_parser.source_code_parser import SourceCodeParser


@pytest.fixture
def valid_function_entity() -> FunctionEntity:
    """
    This fixture creates and returns a valid instance of FunctionEntity with a name, docstring, signature, and file_path.
    """
    return FunctionEntity(name="test_function", docstring="This is a test function.", signature="def test_function(arg1, arg2):", file_path="src/my_module/my_file.py")


@pytest.mark.integration
def test_should_search_code_entity_with_real_storage(valid_function_entity: FunctionEntity):
    """
    This test checks if the SearchService correctly retrieves a previously indexed code entity with a real storage backend.
    Note: This assumes that a real storage backend is configured and accessible.
    """
    # First, we index a valid code entity with the IndexService
    index_service = IndexService()
    try:
        index_service.index(valid_function_entity)
    except Exception as e:
        pytest.fail(f"Indexing failed with exception: {str(e)}")

    # Then, we use the SearchService to search for the previously indexed entity
    search_service = SearchService()
    try:
        result = search_service.search(valid_function_entity.to_description())

        # Assert that the returned result includes the previously indexed entity
        assert valid_function_entity in [scored_entity.entity for scored_entity in result.entities]
    except Exception as e:
        pytest.fail(f"Search failed with exception: {str(e)}")


@pytest.fixture
def valid_function_entities() -> List[FunctionEntity]:
    """
    This fixture creates and returns a list of valid instances of FunctionEntity.
    """
    return [
        FunctionEntity(name="test_function1", docstring="This is a function to add two numbers.", signature="def test_function1(arg1, arg2):", file_path="src/my_module/my_file1.py"),
        FunctionEntity(name="test_function2", docstring="This is a function to subtract numbers.", signature="def test_function2(arg1, arg2):", file_path="src/my_module/my_file2.py"),
        FunctionEntity(name="test_function3", docstring="This function multiply two numbers.", signature="def test_function3(*args):", file_path="src/my_module/my_file3.py"),
    ]


@pytest.mark.integration
def test_search_service_retrieves_indexed_entities_correctly(valid_function_entities: List[FunctionEntity], setup_and_teardown_redis):
    """
    This test checks if the SearchService correctly retrieves multiple previously indexed code entities with a real storage backend.
    It also checks the order of the results to evaluate the quality of the natural language search.
    Note: This assumes that a real storage backend is configured and accessible.
    """
    index_service = IndexService()
    try:
        for entity in valid_function_entities:
            index_service.index(entity)
    except Exception as e:
        pytest.fail(f"Indexing failed with exception: {str(e)}")

    search_service = SearchService()

    search_query = "subtract two numbers."
    result = search_service.search(search_query)

    for entity_with_score in result.entities:
        print(f"Found entity score: {entity_with_score.score}")
        print(f"Entity description: {entity_with_score.entity.to_description()}")

    # Convert list of ScoredEntity to list of FunctionEntity for easy comparison
    result_entities = [scored_entity.entity for scored_entity in result.entities]


    # Assert that all relevant indexed entities are in the search result
    relevant_entities = [entity for entity in valid_function_entities if "subtract" in entity.docstring]
    for entity in relevant_entities:
        assert entity in result_entities

    # Check that the most relevant entity is first in the result
    most_relevant_entity = next(entity for entity in valid_function_entities if "subtract" in entity.docstring)
    assert result_entities[0] == most_relevant_entity, "the returned first entity is not the most relevant one"


@pytest.mark.integration
def test_parser_and_search_integration(setup_and_teardown_redis):
    """
    This test checks if the system can correctly parse a Python file, index the parsed code entities, and then retrieve them via search.
    It tests both SourceCodeParser and SearchService in an integrated manner.
    Note: This assumes that a real storage backend and OpenAI embedding creator are configured and accessible.
    """
    index_service = IndexService()
    search_service = SearchService()
    parser = SourceCodeParser()

    with tempfile.NamedTemporaryFile(suffix=".py") as temp:
        # Arrange
        code_string = textwrap.dedent("""
        \"\"\"A simple Python file containing a function to subtract two numbers.\"\"\"
        
        def subtract(a: int, b: int):
            \"\"\"This is a function that subtracts two numbers\"\"\"
            return a - b
        """)
        temp.write(code_string.encode('utf-8'))
        temp.seek(0)

        # Parse the source code
        module_entity = parser.parse_source_code(temp.name)

        try:
            index_service.index(module_entity)
        except Exception as e:
            pytest.fail(f"Indexing failed with exception: {str(e)}")

        # Perform a search operation
        search_query = "subtract two numbers."
        result = search_service.search(search_query)

        # Assert that the search result contains the indexed function entity
        result_entities = [scored_entity.entity for scored_entity in result.entities]
        assert module_entity.functions["subtract"] in result_entities, "The subtract function was not found in the search results"

        # Check that the indexed function entity is first in the search result
        assert result_entities[0] == module_entity.functions["subtract"], "The subtract function is not the most relevant result"
