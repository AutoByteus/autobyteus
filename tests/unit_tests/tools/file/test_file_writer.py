# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/tests/unit_tests/tools/test_file_writer.py
import pytest
import os
from autobyteus.tools.file.file_writer import FileWriter

@pytest.fixture
def file_writer():
    return FileWriter()

def test_should_create_file_with_specified_content(file_writer):
    path = "./test_file1.txt"
    content = "Test Content 1"
    expected_message = "File created at ./test_file1.txt"
    result = file_writer.execute(path=path, content=content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content
    os.remove(path)  # cleanup

def test_should_create_file_in_non_existing_directory(file_writer):
    path = "./subdir/test_file2.txt"
    content = "Test Content 2"
    expected_message = "File created at ./subdir/test_file2.txt"
    result = file_writer.execute(path=path, content=content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content
    os.remove(path)  # cleanup
    os.rmdir("./subdir")  # cleanup

def test_should_raise_error_when_path_not_provided(file_writer):
    with pytest.raises(ValueError, match="The 'path' keyword argument must be specified."):
        file_writer.execute(content="Test Content")

def test_tool_usage(file_writer):
    expected_usage = 'FileWriter: Creates a file with specified content. Usage: <<<FileWriter(path="file_path", content="file_content")>>>, where "file_path" is the path to create the file and "file_content" is the content to write to the file.'
    assert file_writer.tool_usage() == expected_usage

def test_tool_usage_xml(file_writer):
    expected_usage_xml = '''FileWriter: Creates a file with specified content. Usage:
    <command name="FileWriter">
    <arg name="path">file_path</arg>
    <arg name="content">file_content</arg>
    </command>
    where "file_path" is the path to create the file and "file_content" is the content to write to the file.
    '''
    assert file_writer.tool_usage_xml() == expected_usage_xml