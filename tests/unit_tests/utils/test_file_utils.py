import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
from autobyteus.utils.file_utils import resolve_safe_path, get_default_download_folder

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
    
    # We must patch get_default_download_folder to return our temp downloads dir
    # so the utility recognizes it as a valid root.
    with patch("autobyteus.utils.file_utils.get_default_download_folder", return_value=str(downloads)):
        result = resolve_safe_path(str(target_path), workspace)
        assert result == target_path

def test_resolve_safe_path_temp_folder(mock_dirs):
    workspace, _ = mock_dirs
    # Use the actual system temp dir as it is whitelisted by the utility
    temp_dir = Path(tempfile.gettempdir()).resolve()
    target_path = temp_dir / "temp_file.tmp"
    
    result = resolve_safe_path(str(target_path), workspace)
    assert result == target_path

def test_resolve_safe_path_traversal_attack(mock_dirs):
    workspace, _ = mock_dirs
    
    # Patch temp dir to ensure our test environment (which is in /tmp) isn't accidentally whitelisted
    with patch("tempfile.gettempdir", return_value="/dummy/temp"):
        # Attempt to go up out of workspace
        # Since workspace is in /tmp, and we disabled /tmp whitelist, this should fail
        with pytest.raises(ValueError, match="Security Violation"):
            resolve_safe_path("../outside.txt", workspace)
            
        # Attempt absolute path to forbidden location (e.g., parent of workspace)
        forbidden_path = workspace.parent / "secret.txt"
        with pytest.raises(ValueError, match="Security Violation"):
            resolve_safe_path(str(forbidden_path), workspace)

def test_resolve_safe_path_absolute_forbidden(mock_dirs):
    workspace, _ = mock_dirs
    
    # Test a completely unrelated path (like root on linux)
    # We use a path that is definitely not in workspace, downloads, or temp
    # Using the root of the temp path fixture (which is usually /tmp/pytest-of-user/...)
    # We go up enough levels or just pick a different root.
    
    # On linux /bin is usually safe to check as "forbidden" for writing
    forbidden_path = Path("/bin/sh") 
    
    # If we are running where /bin doesn't exist (windows), pick another.
    if os.name == 'nt':
        forbidden_path = Path("C:\\Windows\\System32\\cmd.exe")
        
    with pytest.raises(ValueError, match="Security Violation"):
        resolve_safe_path(str(forbidden_path), workspace)
