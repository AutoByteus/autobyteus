import pytest
import os
from src.tools.file_generator import FileGenerator

@pytest.fixture
def file_gen():
    return FileGenerator()

def test_should_create_file_with_specified_content(file_gen):
    path = "./test_file1.txt"
    content = "Test Content 1"
    expected_message = "File created at ./test_file1.txt"
    result = file_gen.execute(path, content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content

def test_should_create_file_in_non_existing_directory(file_gen):
    path = "./subdir/test_file2.txt"
    content = "Test Content 2"
    expected_message = "File created at ./subdir/test_file2.txt"
    result = file_gen.execute(path, content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content
    os.remove(path)  # cleanup
    os.rmdir("./subdir")  # cleanup
