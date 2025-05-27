# file: autobyteus/autobyteus/cli/__init__.py
"""
Command-Line Interface (CLI) utilities for interacting with AutoByteUs components.
"""
# MODIFIED: Import the agent_cli module itself
from . import agent_cli 

# Optionally, you could also directly export the run function if preferred:
# from .agent_cli import run as run_agent_session 
# And then __all__ would be ["run_agent_session"]
# But to match user's agent_cli.run() syntax, exposing the module is better.

__all__ = [
    "agent_cli", # MODIFIED: Export the agent_cli module
]
