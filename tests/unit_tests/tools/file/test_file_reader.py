# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/tests/unit_tests/tools/test_file_reader.py
import pytest
import os
from autobyteus.tools.file.file_reader import FileReader

@pytest.fixture
def file_reader():
    return FileReader()

@pytest.fixture
def test_file(tmp_path):
    file_path = tmp_path / "test_file.txt"
    with open(file_path, 'w') as f:
        f.write("Test Content")
    return file_path

def test_should_read_file_content(file_reader, test_file):
    content = file_reader.execute(path=str(test_file))
    assert content == "Test Content"

def test_should_raise_error_when_file_not_found(file_reader):
    with pytest.raises(FileNotFoundError):
        file_reader.execute(path="non_existent_file.txt")

def test_should_raise_error_when_path_not_provided(file_reader):
    with pytest.raises(ValueError, match="The 'path' keyword argument must be specified."):
        file_reader.execute()

def test_tool_usage(file_reader):
    expected_usage = 'FileReader: Reads content from a specified file. Usage: <<<FileReader(path="file_path")>>>, where "file_path" is the path to the file to be read.'
    assert file_reader.tool_usage() == expected_usage

def test_tool_usage_xml(file_reader):
    expected_usage_xml = '''FileReader: Reads content from a specified file. Usage:
    <command name="FileReader">
    <arg name="path">file_path</arg>
    </command>
    where "file_path" is the path to the file to be read.
    '''
    assert file_reader.tool_usage_xml() == expected_usage_xml