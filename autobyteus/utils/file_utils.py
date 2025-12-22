# File: autobyteus/utils/file_utils.py

import os
import platform
import tempfile
from pathlib import Path
from typing import Union

def get_default_download_folder() -> str:
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.path.expanduser("~"), "Downloads")
    elif system == "Darwin":  # macOS
        return os.path.join(os.path.expanduser("~"), "Downloads")
    elif system == "Linux":
        return os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        return os.path.join(os.path.expanduser("~"), "Downloads")  # Fallback

def resolve_safe_path(user_path: str, workspace_root: Union[str, Path]) -> Path:
    """
    Resolves a file path and ensures it is contained within allowed safe directories.
    
    Allowed directories:
    1. The Agent's Workspace (workspace_root)
    2. The User's Downloads directory
    3. The System Temporary directory
    
    Args:
        user_path: The relative or absolute path provided by the user/tool.
        workspace_root: The root directory of the agent's workspace.
        
    Returns:
        The resolved absolute Path object.
        
    Raises:
        ValueError: If the path is outside the allowed directories.
    """
    workspace = Path(workspace_root).resolve()
    downloads = Path(get_default_download_folder()).resolve()
    temp_dir = Path(tempfile.gettempdir()).resolve()
    
    path_obj = Path(user_path)
    
    # If absolute, check directly. If relative, resolve against workspace.
    if path_obj.is_absolute():
        target = path_obj.resolve()
    else:
        target = (workspace / path_obj).resolve()
    
    # Allowed roots list
    allowed_roots = [workspace, downloads, temp_dir]
    
    is_safe = False
    for root in allowed_roots:
        # Check if target is equal to or a subpath of root
        try:
            target.relative_to(root)
            is_safe = True
            break
        except ValueError:
            continue
            
    if not is_safe:
        raise ValueError(
            f"Security Violation: Path '{user_path}' is not within allowed directories "
            f"(Workspace: {workspace}, Downloads: {downloads}, or Temp: {temp_dir})."
        )
        
    return target
