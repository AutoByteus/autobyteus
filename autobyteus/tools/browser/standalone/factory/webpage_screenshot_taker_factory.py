from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.webpage_screenshot_taker import WebPageScreenshotTaker
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.tool_config import ToolConfig

class WebPageScreenshotTakerFactory(ToolFactory):
    def create_tool(self, config: Optional['ToolConfig'] = None) -> WebPageScreenshotTaker:
        """
        Creates an instance of WebPageScreenshotTaker.
        The 'config' parameter is ignored by this factory.
        """
        return WebPageScreenshotTaker()
