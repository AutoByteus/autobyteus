"""
File: autobyteus/tools/browser/standalone/webpage_reader.py
This module provides a WebPageReader tool for reading and cleaning HTML content from webpages.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from brui_core.ui_integrator import UIIntegrator 
from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class WebPageReader(BaseTool, UIIntegrator):
    """
    A class that reads and cleans the HTML content from a given webpage using Playwright.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self, config=config)
        UIIntegrator.__init__(self) 
        
        cleaning_mode_to_use = CleaningMode.THOROUGH
        if config:
            cleaning_mode_value = config.get('cleaning_mode') 
            if cleaning_mode_value:
                if isinstance(cleaning_mode_value, str):
                    try:
                        cleaning_mode_to_use = CleaningMode(cleaning_mode_value.upper())
                    except ValueError:
                        logger.warning(f"Invalid cleaning_mode string '{cleaning_mode_value}' in config for WebPageReader. Using THOROUGH.")
                        cleaning_mode_to_use = CleaningMode.THOROUGH
                elif isinstance(cleaning_mode_value, CleaningMode):
                    cleaning_mode_to_use = cleaning_mode_value
                else:
                     logger.warning(f"Invalid type for cleaning_mode in config for WebPageReader. Using THOROUGH.")
        
        self.cleaning_mode = cleaning_mode_to_use
        logger.debug(f"WebPageReader initialized with cleaning_mode: {self.cleaning_mode}")

    @classmethod
    def get_description(cls) -> str:
        return "Reads and cleans the HTML content from a given webpage URL using Playwright."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        """Schema for arguments passed to the execute method."""
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url", 
            param_type=ParameterType.STRING,
            description="The URL of the webpage to read content from.",
            required=True
        ))
        return schema
        
    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]:
        """Schema for parameters to configure the WebPageReader instance itself."""
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="cleaning_mode",
            param_type=ParameterType.ENUM,
            description="Level of HTML content cleanup for webpage content. BASIC or THOROUGH.",
            required=False,
            default_value="THOROUGH",
            enum_values=[mode.name for mode in CleaningMode]
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str) -> str:
        logger.info(f"WebPageReader executing for agent {context.agent_id} with URL: '{url}'")

        try:
            await self.initialize()
            if not self.page:
                 logger.error("Playwright page not initialized in WebPageReader.")
                 raise RuntimeError("Playwright page not available for WebPageReader.")

            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page_content = await self.page.content()
            
            cleaned_content = clean(page_content, mode=self.cleaning_mode)
            
            return f'''here is the html of the web page
<WebPageContentStart>
{cleaned_content}
</WebPageContentEnd>
'''
        except Exception as e:
            logger.error(f"Error reading webpage at URL '{url}': {e}", exc_info=True)
            raise RuntimeError(f"WebPageReader failed for URL '{url}': {str(e)}")
        finally:
            await self.close()
