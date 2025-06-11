from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.utils.html_cleaner import CleaningMode
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.tool_config import ToolConfig
    from autobyteus.tools.base_tool import BaseTool

class BrowserSessionAwareWebPageReaderFactory(ToolFactory):
    def __init__(self, content_cleanup_level: CleaningMode = CleaningMode.THOROUGH):
        self.content_cleanup_level = content_cleanup_level

    def create_tool(self, config: Optional['ToolConfig'] = None) -> BrowserSessionAwareWebPageReader:
        """
        Creates an instance of BrowserSessionAwareWebPageReader.
        The 'config' parameter is ignored; configuration is set during factory initialization.
        """
        # This factory passes its own configuration to the tool's constructor.
        # The tool's constructor expects a ToolConfig object.
        from autobyteus.tools.tool_config import ToolConfig as ConcreteToolConfig
        
        tool_creation_config = ConcreteToolConfig(
            params={"cleaning_mode": self.content_cleanup_level}
        )
        return BrowserSessionAwareWebPageReader(config=tool_creation_config)
