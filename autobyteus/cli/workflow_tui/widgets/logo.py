# file: autobyteus/autobyteus/cli/workflow_tui/widgets/logo.py
"""
Defines a widget to display the AutoByteus ASCII art logo and tagline.
"""
from rich.text import Text
from textual.widgets import Static
from textual.containers import Vertical

class Logo(Vertical):
    """A widget to display the AutoByteus ASCII art logo and tagline."""

    def compose(self) -> None:
        logo_text = Text(
            """
    _         _           _     _
   / \\  _   _| |_ ___  __| | __| |_
  / _ \\| | | | __/ _ \\/ _` |/ _` | |
 / ___ \\ |_| | ||  __/ (_| | (_| | |
/_/   \\_\\__,_|\\__\\___|\\__,_|\\__,_|_|
""",
            justify="center",
        )
        logo_text.highlight_regex(r"Auto", "bold cyan")
        logo_text.highlight_regex(r"Byteus", "bold magenta")
        
        yield Static(logo_text, classes="logo-art")
        yield Static("Orchestrating AI Agent Teams.", classes="logo-tagline")
