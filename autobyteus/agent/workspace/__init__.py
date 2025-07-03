# file: autobyteus/autobyteus/agent/workspace/__init__.py
"""
Defines the agent's workspace or working environment.
"""
from .base_workspace import BaseAgentWorkspace
from .workspace_config import WorkspaceConfig

__all__ = [
    "BaseAgentWorkspace",
    "WorkspaceConfig",
]
