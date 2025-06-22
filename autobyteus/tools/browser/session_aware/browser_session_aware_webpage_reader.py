# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_reader.py

import logging
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class BrowserSessionAwareWebPageReader(BrowserSessionAwareTool):
    """
    A session-aware tool to read and clean HTML content from the current page
    in a shared browser session.
    """
    def __init__(self, config: Optional[ToolConfig] = None): 
        super().__init__(config=config)
        
        cleaning_mode_to_use = CleaningMode.THOROUGH 
        if config:
            cleaning_mode_value = config.get('cleaning_mode')
            if cleaning_mode_value:
                if isinstance(cleaning_mode_value, str):
                    try:
                        cleaning_mode_to_use = CleaningMode(cleaning_mode_value.upper())
                    except ValueError:
                        cleaning_mode_to_use = CleaningMode.THOROUGH
                elif isinstance(cleaning_mode_value, CleaningMode):
                    cleaning_mode_to_use = cleaning_mode_value
        
        self.cleaning_mode = cleaning_mode_to_use
        logger.debug(f"BrowserSessionAwareWebPageReader initialized with cleaning_mode: {self.cleaning_mode}")

    @classmethod
    def get_name(cls) -> str: 
        return "WebPageReader"

    @classmethod
    def get_description(cls) -> str:
        return ("Reads and cleans the HTML content from the current page in a shared browser session. "
                "The level of HTML cleanup can be configured at tool instantiation.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="webpage_url", 
            param_type=ParameterType.STRING,
            description="URL of the webpage. Required if no browser session is active or to ensure context. Tool reads current page content after navigation if applicable.",
            required=True 
        ))
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: 
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="cleaning_mode",
            param_type=ParameterType.ENUM,
            description="Level of HTML content cleanup (BASIC or THOROUGH). Applied to the read webpage content.",
            required=False,
            default_value="THOROUGH",
            enum_values=[mode.name for mode in CleaningMode]
        ))
        return schema

    async def perform_action(
        self, 
        shared_session: SharedBrowserSession,
        webpage_url: str 
    ) -> str: 
        logger.info(f"BrowserSessionAwareWebPageReader performing action. Current page URL: {shared_session.page.url}, cleaning_mode: {self.cleaning_mode}")
        
        try:
            page_content = await shared_session.page.content()
            cleaned_content = clean(page_content, self.cleaning_mode)
            logger.debug(f"Read and cleaned content from {shared_session.page.url}. Cleaned length: {len(cleaned_content)}")
            return cleaned_content
        except Exception as e:
            logger.error(f"Error reading page content in shared session from {shared_session.page.url}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to read page content from shared session: {str(e)}")
