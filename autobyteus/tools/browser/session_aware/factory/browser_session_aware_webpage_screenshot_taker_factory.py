from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker

class BrowserSessionAwareWebPageScreenshotTakerFactory(ToolFactory):
    def create_tool(self) -> BrowserSessionAwareWebPageScreenshotTaker:
        return BrowserSessionAwareWebPageScreenshotTaker()