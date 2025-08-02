# file: autobyteus/autobyteus/cli/agent_team_tui/widgets/status_bar.py
"""
Defines the status bar widget for the TUI.
"""

from textual.widgets import Footer

class StatusBar(Footer):
    """A simple footer widget that displays key bindings."""

    def __init__(self) -> None:
        super().__init__()
        # This will be automatically populated by Textual's binding system.
        # You can add more status information here if needed in the future.
