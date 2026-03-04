# File: autobyteus/utils/file_utils.py

import os
import platform
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
    Resolves a file path.

    - Absolute paths are returned as-is (the caller knows what they want).
    - Relative paths are resolved against workspace_root.

    Args:
        user_path: The relative or absolute path provided by the user/tool.
        workspace_root: The root directory used to resolve relative paths.

    Returns:
        The resolved absolute Path object.
    """
    path_obj = Path(user_path)

    if path_obj.is_absolute():
        return path_obj.resolve()

    workspace = Path(workspace_root).resolve()
    return (workspace / path_obj).resolve()
