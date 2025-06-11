from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
from autobyteus.utils.html_cleaner import CleaningMode
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.tool_config import ToolConfig

class WebPageReaderFactory(ToolFactory):
    def __init__(self, cleaning_mode: CleaningMode = CleaningMode.THOROUGH):
        self.cleaning_mode = cleaning_mode

    def create_tool(self, config: Optional['ToolConfig'] = None) -> WebPageReader:
        """
        Creates an instance of WebPageReader.
        The 'config' parameter is ignored; configuration is set during factory initialization.
        """
        # This factory passes its own configuration to the tool's constructor.
        # The tool's constructor expects a ToolConfig object.
        from autobyteus.tools.tool_config import ToolConfig as ConcreteToolConfig
        
        tool_creation_config = ConcreteToolConfig(
            params={"cleaning_mode": self.cleaning_mode}
        )
        return WebPageReader(config=tool_creation_config)
