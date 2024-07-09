# tests/integration_tests/db/repositories/test_prompt_version_repository_integration.py
import pytest

from autobyteus.prompt.storage.prompt_version_model import PromptVersionModel
from autobyteus.prompt.storage.prompt_version_repository import PromptVersionRepository

@pytest.fixture()
def prompt_version_repository():
    return PromptVersionRepository()

def test_given_prompt_version_when_created_then_saved_in_database(prompt_version_repository: PromptVersionRepository):
    # Given: A sample PromptVersionModel object
    test_version = PromptVersionModel(prompt_name="TestPrompt", version_no=1, prompt_content="Sample Prompt")
    
    # When: The object is added to the database
    created_version = prompt_version_repository.create_version(test_version)
    
    # Then: The object should be saved in the database with an ID assigned
    assert created_version.id is not None
    assert created_version.prompt_content == "Sample Prompt"


def test_given_prompt_version_id_when_retrieved_then_correct_object_returned(prompt_version_repository: PromptVersionRepository):
    # Given: A sample PromptVersionModel object saved in the database
    test_version = PromptVersionModel(prompt_name="TestPrompt", version_no=2, prompt_content="Sample Prompt 2")
    saved_version = prompt_version_repository.create_version(test_version)
    
    
    # When: The object is retrieved by its prompt_name and version_no
    retrieved_version = prompt_version_repository.get_version("TestPrompt", 2)
    
    # Then: The correct object should be returned
    assert retrieved_version.id == saved_version.id
    assert retrieved_version.prompt_content == "Sample Prompt 2"


def test_given_prompt_name_when_retrieved_current_effective_then_correct_object_returned(prompt_version_repository: PromptVersionRepository):
    # Given: A sample PromptVersionModel object saved in the database with is_current_effective set to True
    test_version = PromptVersionModel(prompt_name="TestPrompt", version_no=3, prompt_content="Sample Prompt 3", is_current_effective=True)
    saved_version = prompt_version_repository.create_version(test_version)
    
    # When: The current effective version is retrieved by its prompt_name
    effective_version = prompt_version_repository.get_current_effective_version("TestPrompt")
    
    # Then: The correct object with is_current_effective as True should be returned
    assert effective_version.id == saved_version.id
    assert effective_version.is_current_effective


def test_given_prompt_name_when_retrieved_latest_then_correct_object_returned(prompt_version_repository: PromptVersionRepository):
    # Given: Multiple PromptVersionModel objects saved in the database
    version1 = PromptVersionModel(prompt_name="TestPrompt", version_no=4, prompt_content="Sample Prompt 4")
    version2 = PromptVersionModel(prompt_name="TestPrompt", version_no=5, prompt_content="Sample Prompt 5")
    prompt_version_repository.create_version(version1)
    prompt_version_repository.create_version(version2)
    
    # When: The latest version is retrieved by its prompt_name
    latest_version = prompt_version_repository.get_latest_created_version("TestPrompt")

    # Then: The object with the highest version_no should be returned
    assert latest_version.version_no == 5
    assert latest_version.prompt_content == "Sample Prompt 5"


def test_given_prompt_version_when_deleted_then_no_longer_in_database(prompt_version_repository: PromptVersionRepository):
    # Given: A sample PromptVersionModel object saved in the database
    test_version = PromptVersionModel(prompt_name="TestPrompt", version_no=6, prompt_content="Sample Prompt 6")
    saved_version = prompt_version_repository.create_version(test_version)
    
    # When: The object is deleted by its prompt_name and version_no
    prompt_version_repository.delete_version("TestPrompt", 6)
    
    # Then: The object should no longer be present in the database
    retrieved_version = prompt_version_repository.get_version("TestPrompt", 6)
    assert retrieved_version is None


def test_given_prompt_name_when_oldest_deleted_then_oldest_version_no_longer_in_database(prompt_version_repository: PromptVersionRepository):
    # Given: Multiple PromptVersionModel objects saved in the database
    version7 = PromptVersionModel(prompt_name="TestPrompt", version_no=7, prompt_content="Sample Prompt 7")
    version8 = PromptVersionModel(prompt_name="TestPrompt", version_no=8, prompt_content="Sample Prompt 8")
    prompt_version_repository.create_version(version7)
    prompt_version_repository.create_version(version8)
    
    # When: The oldest version is deleted by its prompt_name
    prompt_version_repository.delete_oldest_version("TestPrompt")
    
    # Then: The object with the lowest version_no should no longer be present in the database
    oldest_version = prompt_version_repository.get_version("TestPrompt", 7)
    assert oldest_version is None
