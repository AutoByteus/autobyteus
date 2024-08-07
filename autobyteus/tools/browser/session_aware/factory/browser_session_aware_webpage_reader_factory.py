from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.utils.html_cleaner import CleaningMode

class BrowserSessionAwareWebPageReaderFactory(ToolFactory):
    def __init__(self, content_cleanup_level: CleaningMode = CleaningMode.THOROUGH):
        self.content_cleanup_level = content_cleanup_level

    def create_tool(self) -> BrowserSessionAwareWebPageReader:
        return BrowserSessionAwareWebPageReader(cleaning_mode=self.content_cleanup_level)