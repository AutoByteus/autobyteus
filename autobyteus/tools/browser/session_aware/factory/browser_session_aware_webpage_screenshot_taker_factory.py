from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.tool_config import ToolConfig

class BrowserSessionAwareWebPageScreenshotTakerFactory(ToolFactory):
    def create_tool(self, config: Optional['ToolConfig'] = None) -> BrowserSessionAwareWebPageScreenshotTaker:
        """
        Creates an instance of BrowserSessionAwareWebPageScreenshotTaker.
        The 'config' parameter is ignored by this factory.
        """
        return BrowserSessionAwareWebPageScreenshotTaker()
