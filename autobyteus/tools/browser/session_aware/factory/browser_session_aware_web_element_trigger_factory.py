from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger

class BrowserSessionAwareWebElementTriggerFactory(ToolFactory):
    def create_tool(self) -> BrowserSessionAwareWebElementTrigger:
        return BrowserSessionAwareWebElementTrigger()