import pytest
from src.tools.file_generator import FileGenerator

# Tests for FileGenerator
@pytest.mark.parametrize('path, content, expected_message', [
    ('./test_file1.txt', 'Test Content 1', 'File created at ./test_file1.txt'),
    ('./subdir/test_file2.txt', 'Test Content 2', 'File created at ./subdir/test_file2.txt')
])
def test_file_generator(path, content, expected_message):
    file_gen = FileGenerator()
    result = file_gen.execute(path, content)
    assert result == expected_message
    with open(path, 'r') as file:
        assert file.read() == content

