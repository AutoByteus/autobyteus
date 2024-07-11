# tests/unit_tests/source_code_tree/file_explorer/test_traversal_ignore_strategy.py

import os
import tempfile
from autobyteus.codeverse.core.file_explorer.traversal_ignore_strategy.git_ignore_strategy import GitIgnoreStrategy

def test_git_ignore_strategy_ignore_matched_pattern():
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        gitignore_file = os.path.join(tmpdirname, '.gitignore')
        with open(gitignore_file, 'w') as f:
            f.write('*.txt\n')
        
        git_ignore_strategy = GitIgnoreStrategy(tmpdirname)

        # Act
        should_ignore = git_ignore_strategy.should_ignore('test.txt')

        # Assert
        assert should_ignore is True


def test_git_ignore_strategy_not_ignore_unmatched_pattern():
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        gitignore_file = os.path.join(tmpdirname, '.gitignore')
        with open(gitignore_file, 'w') as f:
            f.write('*.txt\n')
        
        git_ignore_strategy = GitIgnoreStrategy(tmpdirname)

        # Act
        should_ignore = git_ignore_strategy.should_ignore('test.py')

        # Assert
        assert should_ignore is False


def test_git_ignore_strategy_not_ignore_no_gitignore_file():
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        git_ignore_strategy = GitIgnoreStrategy(tmpdirname)

        # Act
        should_ignore = git_ignore_strategy.should_ignore('test.txt')

        # Assert
        assert should_ignore is False


def test_git_ignore_strategy_ignore_dot_folder():
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        gitignore_file = os.path.join(tmpdirname, '.gitignore')
        with open(gitignore_file, 'w') as f:
            f.write('.folder/\n')
        
        git_ignore_strategy = GitIgnoreStrategy(tmpdirname)

        # Act
        should_ignore = git_ignore_strategy.should_ignore(tmpdirname +'/.folder')

        # Assert
        assert should_ignore is True