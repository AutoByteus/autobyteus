# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/tests/unit_tests/tools/test_file_writer.py
import pytest
import os
import tempfile
import shutil
from autobyteus.tools.file.file_writer import FileWriter

@pytest.fixture
def file_writer():
    return FileWriter()

@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_should_create_file_with_specified_content(file_writer, temp_dir):
    path = os.path.join(temp_dir, "test_file1.txt")
    content = "Test Content 1"
    expected_message = f"File created at {path}"
    result = file_writer._execute(path=path, content=content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content

def test_should_create_file_in_non_existing_directory(file_writer, temp_dir):
    path = os.path.join(temp_dir, "subdir", "test_file2.txt")
    content = "Test Content 2"
    expected_message = f"File created at {path}"
    result = file_writer._execute(path=path, content=content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content

def test_should_raise_error_when_path_not_provided(file_writer):
    with pytest.raises(ValueError, match="The 'path' keyword argument must be specified."):
        file_writer._execute(content="Test Content")

def test_should_raise_error_when_content_not_provided(file_writer, temp_dir):
    path = os.path.join(temp_dir, "test_file.txt")
    with pytest.raises(ValueError, match="The 'content' keyword argument must be specified."):
        file_writer._execute(path=path)

def test_tool_usage_xml(file_writer):
    expected_usage_xml = '''FileWriter: Creates a file with specified content. Usage:
    <command name="FileWriter">
    <arg name="path">file_path</arg>
    <arg name="content">file_content</arg>
    </command>
    where "file_path" is the path to create the file and "file_content" is the content to write to the file.
    '''
    assert file_writer.tool_usage_xml() == expected_usage_xml

def test_get_name():
    assert FileWriter.get_name() == "FileWriter"

def test_should_create_file_with_empty_content(file_writer, temp_dir):
    path = os.path.join(temp_dir, "empty_file.txt")
    content = ""
    expected_message = f"File created at {path}"
    result = file_writer._execute(path=path, content=content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content

def test_should_overwrite_existing_file(file_writer, temp_dir):
    path = os.path.join(temp_dir, "existing_file.txt")
    
    # Create initial file
    initial_content = "Initial content"
    file_writer._execute(path=path, content=initial_content)
    
    # Overwrite with new content
    new_content = "New content"
    expected_message = f"File created at {path}"
    result = file_writer._execute(path=path, content=new_content)
    assert result == expected_message
    
    with open(path, 'r') as file:
        assert file.read() == new_content
