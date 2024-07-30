from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch
from autobyteus.utils.html_cleaner import CleaningMode

class GoogleSearchFactory(ToolFactory):
    def __init__(self, cleaning_mode: CleaningMode = CleaningMode.THOROUGH):
        self.cleaning_mode = cleaning_mode

    def create_tool(self) -> GoogleSearch:
        return GoogleSearch(cleaning_mode=self.cleaning_mode)