# file: autobyteus/autobyteus/cli/agent_team_tui/widgets/logo.py
"""
Defines a widget to display the AutoByteus ASCII art logo and tagline.
"""
from rich.text import Text
from textual.widgets import Static
from textual.containers import Vertical

class Logo(Vertical):
    """A widget to display the AutoByteus logo and tagline."""

    def compose(self) -> None:
        # A simple, clean, single-line text logo that is more readable
        # and respects that "AutoByteus" is one word.
        logo_text = Text(justify="center")
        logo_text.append("Auto", style="bold cyan")
        logo_text.append("Byteus", style="bold magenta")
        
        yield Static(logo_text, classes="logo-art")
        yield Static("Orchestrating AI Agent Teams.", classes="logo-tagline")
