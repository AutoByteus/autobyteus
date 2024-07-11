import pytest
import os
import tempfile
from autobyteus.codeverse.core.file_explorer.directory_traversal import DirectoryTraversal
from autobyteus.workspaces.setting.project_types import ProjectType
from autobyteus.workspaces.workspace_directory_tree import WorkspaceDirectoryTree
from autobyteus.workspaces.workspace_tools.workspace_refactorer.python_project_refactorer import PythonProjectRefactorer
from autobyteus.workspaces.setting.workspace_setting import WorkspaceSetting


def test_should_print_refactored_code_for_valid_files(capsys):
    """Ensure that refactored code is printed for valid Python files and not for __init__.py files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.makedirs(os.path.join(tmpdirname, 'src', 'project'))
        
        # Python file with a function without a docstring
        code1 = """
                def add(a, b):
                    return a + b
                """
        file_path_1 = os.path.join(tmpdirname, 'src', 'project', 'math_utils.py')
        with open(file_path_1, 'w') as f:
            f.write(code1)
        
        # __init__.py file
        file_path_2 = os.path.join(tmpdirname, 'src', 'project', '__init__.py')
        with open(file_path_2, 'w') as f:
            f.write("# init file")
        
        dir_traversal = DirectoryTraversal()
        directory_tree = WorkspaceDirectoryTree(dir_traversal.build_tree(tmpdirname))
        workspace_setting = WorkspaceSetting(root_path=tmpdirname, project_type=ProjectType.PYTHON, directory_tree=directory_tree)
        
        refactorer = PythonProjectRefactorer(workspace_setting)
        refactorer.refactor()
        
        captured = capsys.readouterr()
        
        # Checking if the refactored code is printed for the correct file path
        assert f"Refactored code for {file_path_1}" in captured.out

        # Making sure it skips the __init__.py file
        assert "__init__.py" not in captured.out


def test_should_construct_prompt_with_file_content():
    """Ensure that the construct_prompt method correctly formats the prompt with file content."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Python file with a function without a docstring
        code = """
                def subtract(a, b):
                    return a - b
                """
        file_path = os.path.join(tmpdirname, 'utils.py')
        with open(file_path, 'w') as f:
            f.write(code)
        
        dir_traversal = DirectoryTraversal()
        directory_tree = dir_traversal.build_tree(tmpdirname)
        workspace_setting = WorkspaceSetting(directory_tree=directory_tree)
        
        refactorer = PythonProjectRefactorer(workspace_setting)
        prompt = refactorer.construct_prompt(file_path)
        
        # Verifying the correct format and content of the constructed prompt
        expected_content = """
                            def subtract(a, b):
                            return a - b
                            """
        assert f"Please examine the source code in file {file_path}" in prompt
        assert expected_content in prompt