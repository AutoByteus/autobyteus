from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.webpage_screenshot_taker import WebPageScreenshotTaker

class WebPageScreenshotTakerFactory(ToolFactory):
    def create_tool(self) -> WebPageScreenshotTaker:
        return WebPageScreenshotTaker()