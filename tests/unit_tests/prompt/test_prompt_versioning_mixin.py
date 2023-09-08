# File: tests/unit_tests/prompt/test_prompt_versioning_mixin.py

import pytest
from unittest.mock import Mock, patch

from autobyteus.prompt.prompt_versioning_mixin import TestPromptVersioningMixin
from autobyteus.db.models.prompt_version_model import PromptVersionModel

class TestPromptVersioningMixin(TestPromptVersioningMixin):
    prompt_name = "TestPromptName"
    default_prompt = "Default Prompt"

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_initialize_with_repository_instance(mock_repo, mock_session_manager):
    mixin = TestPromptVersioningMixin()
    assert mixin.repository == mock_repo.return_value

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_add_first_version_correctly(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_repo.get_latest_created_version.return_value = None
    mixin.add_version("Test Prompt 1")
    
    called_args = mock_repo.create_version.call_args[0][0]
    assert called_args.prompt_name == "TestPromptName"
    assert called_args.version_no == 1
    assert called_args.prompt_content == "Test Prompt 1"
    assert called_args.is_current_effective == False

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_add_subsequent_versions_correctly(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_latest_version = Mock()
    mock_latest_version.version_no = 2
    mock_repo.get_latest_created_version.return_value = mock_latest_version
    mixin.add_version("Test Prompt 3")
    
    called_args = mock_repo.create_version.call_args[0][0]
    assert called_args.prompt_name == "TestPromptName"
    assert called_args.version_no == 3
    assert called_args.prompt_content == "Test Prompt 3"
    assert called_args.is_current_effective == False

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_delete_oldest_version_when_limit_exceeded(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_latest_version = Mock()
    mock_latest_version.version_no = 4
    mock_repo.get_latest_created_version.return_value = mock_latest_version
    mixin.add_version("Test Prompt 5")
    mock_repo.delete_oldest_version.assert_called_once()

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_retrieve_existing_version_content(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_version = Mock()
    mock_version.prompt_content = "Test Prompt 2"
    mock_repo.get_version.return_value = mock_version
    result = mixin.get_version(2)
    assert result == "Test Prompt 2"

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_return_none_for_non_existent_version(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_repo.get_version.return_value = None
    result = mixin.get_version(99)
    assert result is None

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_set_existing_version_as_current_effective(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_version = Mock()
    mock_version.is_current_effective = False
    mock_repo.get_version.return_value = mock_version
    mixin.set_current_effective_version(2)
    assert mock_version.is_current_effective
    mock_repo.create_version.assert_called_once()

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_not_set_non_existent_version_as_current_effective(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_repo.get_version.return_value = None
    mixin.set_current_effective_version(99)
    mock_repo.create_version.assert_not_called()

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_get_current_effective_prompt_from_existing_version(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_version = Mock()
    mock_version.prompt_content = "Test Effective Prompt"
    mock_repo.get_current_effective_version.return_value = mock_version
    result = mixin.get_current_effective_prompt()
    assert result == "Test Effective Prompt"

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_get_default_prompt_when_no_effective_version_exists(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_repo.get_current_effective_version.return_value = None
    mixin.default_prompt = "Default Prompt"
    result = mixin.get_current_effective_prompt()
    assert result == "Default Prompt"

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_load_latest_version_content(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_version = Mock()
    mock_version.prompt_content = "Test Latest Prompt"
    mock_repo.get_latest_created_version.return_value = mock_version
    result = mixin.load_latest_version()
    assert result == "Test Latest Prompt"

@patch("autobyteus.prompt.prompt_versioning_mixin.DatabaseSessionManager")
@patch("autobyteus.prompt.prompt_versioning_mixin.PromptVersionRepository")
def test_should_load_default_prompt_when_no_versions_exist(mock_repo, mock_session_manager):
    mock_repo.return_value = mock_repo
    mixin = TestPromptVersioningMixin()
    mock_repo.get_latest_created_version.return_value = None
    mixin.default_prompt = "Default Prompt"
    result = mixin.load_latest_version()
    assert result == "Default Prompt"
