from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.tool_config import ToolConfig

class BrowserSessionAwareWebElementTriggerFactory(ToolFactory):
    def create_tool(self, config: Optional['ToolConfig'] = None) -> BrowserSessionAwareWebElementTrigger:
        """
        Creates an instance of BrowserSessionAwareWebElementTrigger.
        The 'config' parameter is ignored by this factory.
        """
        return BrowserSessionAwareWebElementTrigger()
