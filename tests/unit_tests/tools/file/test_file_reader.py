# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/tests/unit_tests/tools/test_file_reader.py
import pytest
import os
from unittest.mock import Mock # Added Mock
from autobyteus.tools.file.file_reader import FileReader

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def file_reader():
    return FileReader()

@pytest.fixture
def test_file(tmp_path):
    file_path = tmp_path / "test_file.txt"
    with open(file_path, 'w') as f:
        f.write("Test Content")
    return file_path

@pytest.mark.asyncio
async def test_should_read_file_content(file_reader, test_file, mock_agent_context): # Added mock_agent_context
    content = await file_reader.execute(mock_agent_context, path=str(test_file)) # Added mock_agent_context
    assert content == "Test Content"

@pytest.mark.asyncio
async def test_should_raise_error_when_file_not_found(file_reader, mock_agent_context): # Added mock_agent_context
    with pytest.raises(FileNotFoundError):
        await file_reader.execute(mock_agent_context, path="non_existent_file.txt") # Added mock_agent_context

@pytest.mark.asyncio
async def test_should_raise_error_when_path_not_provided(file_reader, mock_agent_context): # Added mock_agent_context
    with pytest.raises(ValueError, match="The 'path' keyword argument must be specified."):
        await file_reader.execute(mock_agent_context) # Added mock_agent_context

def test_tool_usage_xml(file_reader):
    expected_usage_xml = '''FileReader: Reads content from a specified file. Usage:
    <command name="FileReader">
    <arg name="path">file_path</arg>
    </command>
    where "file_path" is the path to the file to be read.
    '''
    assert file_reader.tool_usage_xml() == expected_usage_xml

def test_get_name():
    assert FileReader.get_name() == "FileReader"

@pytest.mark.asyncio
async def test_file_reader_with_relative_path(tmp_path, mock_agent_context): # Added mock_agent_context
    # Create a test file with relative path
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    file_path = "relative_test.txt"
    with open(file_path, 'w') as f:
        f.write("Relative path content")
    
    file_reader = FileReader()
    content = await file_reader.execute(mock_agent_context, path=file_path) # Added mock_agent_context
    assert content == "Relative path content"
    os.chdir(original_cwd) # Restore CWD

@pytest.mark.asyncio
async def test_file_reader_empty_file(tmp_path, mock_agent_context): # Added mock_agent_context
    # Test reading empty file
    file_path = tmp_path / "empty_file.txt"
    file_path.touch()
    
    file_reader = FileReader()
    content = await file_reader.execute(mock_agent_context, path=str(file_path)) # Added mock_agent_context
    assert content == ""
