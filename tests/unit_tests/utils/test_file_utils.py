import os
import tempfile
import pytest
from pathlib import Path
from autobyteus.utils.file_utils import resolve_safe_path

@pytest.fixture
def mock_dirs(tmp_path):
    """Creates a mock workspace and downloads directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    return workspace, downloads

def test_resolve_safe_path_relative_in_workspace(mock_dirs):
    workspace, _ = mock_dirs

    # Test simple relative path
    result = resolve_safe_path("image.png", workspace)
    assert result == workspace / "image.png"

    # Test nested relative path
    result = resolve_safe_path("assets/image.png", workspace)
    assert result == workspace / "assets" / "image.png"

def test_resolve_safe_path_absolute_in_workspace(mock_dirs):
    workspace, _ = mock_dirs
    abs_path = workspace / "test.txt"

    result = resolve_safe_path(str(abs_path), workspace)
    assert result == abs_path

def test_resolve_safe_path_downloads_folder(mock_dirs):
    workspace, downloads = mock_dirs
    target_path = downloads / "downloaded.file"

    result = resolve_safe_path(str(target_path), workspace)
    assert result == target_path

def test_resolve_safe_path_temp_folder(mock_dirs):
    workspace, _ = mock_dirs
    temp_dir = Path(tempfile.gettempdir()).resolve()
    target_path = temp_dir / "temp_file.tmp"

    result = resolve_safe_path(str(target_path), workspace)
    assert result == target_path

def test_resolve_safe_path_traversal(mock_dirs):
    workspace, _ = mock_dirs

    # Relative traversal resolves against workspace — no error raised
    result = resolve_safe_path("../outside.txt", workspace)
    assert result == (workspace / "../outside.txt").resolve()
    assert result == workspace.parent / "outside.txt"

    # Absolute path outside workspace also resolves as-is — no error raised
    forbidden_path = workspace.parent / "secret.txt"
    result = resolve_safe_path(str(forbidden_path), workspace)
    assert result == forbidden_path

def test_resolve_safe_path_absolute_any_location(mock_dirs):
    workspace, _ = mock_dirs

    # Absolute path to any location resolves as-is — no error raised
    if os.name == 'nt':
        target_path = Path("C:\\Windows\\System32\\cmd.exe")
    else:
        target_path = Path("/bin/sh")

    result = resolve_safe_path(str(target_path), workspace)
    assert result == target_path.resolve()
