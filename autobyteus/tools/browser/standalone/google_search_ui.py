"""
File: autobyteus/tools/browser/google_search_ui.py
This module provides a GoogleSearch tool for performing Google searches using Playwright.
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig # For instantiation config
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Updated
from brui_core.ui_integrator import UIIntegrator # GoogleSearch is also a UIIntegrator
from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Added

logger = logging.getLogger(__name__)

class GoogleSearch(BaseTool, UIIntegrator): # Multiple inheritance
    """
    A tool that allows for performing a Google search using Playwright and retrieving the search results.
    Inherits from BaseTool for tool framework compatibility and UIIntegrator for Playwright integration.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self) # Initialize UIIntegrator

        self.text_area_selector = 'textarea[name="q"]'
        
        cleaning_mode_to_use = CleaningMode.THOROUGH 
        if config:
            cleaning_mode_value = config.get('cleaning_mode') # From instantiation config
            if cleaning_mode_value:
                if isinstance(cleaning_mode_value, str):
                    try:
                        cleaning_mode_to_use = CleaningMode(cleaning_mode_value.upper())
                    except ValueError:
                        logger.warning(f"Invalid cleaning_mode string '{cleaning_mode_value}' in config. Using THOROUGH.")
                        cleaning_mode_to_use = CleaningMode.THOROUGH
                elif isinstance(cleaning_mode_value, CleaningMode):
                    cleaning_mode_to_use = cleaning_mode_value
                else:
                    logger.warning(f"Invalid type for cleaning_mode in config. Using THOROUGH.")
        
        self.cleaning_mode = cleaning_mode_to_use
        logger.debug(f"GoogleSearch initialized with cleaning_mode: {self.cleaning_mode}")

    @classmethod
    def get_description(cls) -> str:
        return "Searches Google for a given query and returns cleaned HTML search results."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        """Schema for arguments passed to the execute method."""
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="query",
            param_type=ParameterType.STRING,
            description="The search query string.",
            required=True
        ))
        # cleaning_mode for execute can be added if runtime override is desired
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: # For instantiation config
        """Schema for parameters to configure the GoogleSearch instance itself."""
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="cleaning_mode",
            param_type=ParameterType.ENUM,
            description="Level of HTML content cleanup for search results. BASIC or THOROUGH.",
            required=False,
            default_value="THOROUGH", # Default for instantiation
            enum_values=[mode.name for mode in CleaningMode]
        ))
        return schema

    async def _execute(self, context: 'AgentContext', query: str) -> str: # Updated signature
        """
        Performs a Google search for the given query.
        'query' is validated by BaseTool.execute().
        """
        logger.info(f"GoogleSearch executing for agent {context.agent_id} with query: '{query}'")

        try:
            await self.initialize() # Initialize Playwright page from UIIntegrator
            if not self.page: # Should be set by initialize()
                 logger.error("Playwright page not initialized in GoogleSearch.")
                 raise RuntimeError("Playwright page not available for Google Search.")

            await self.page.goto('https://www.google.com/')

            textarea = self.page.locator(self.text_area_selector)
            await textarea.click()
            await self.page.type(self.text_area_selector, query) # Use page.type for better control
            await self.page.keyboard.press('Enter')
            
            # Wait for search results to load. Prefer more specific selectors if possible.
            await self.page.wait_for_load_state("networkidle", timeout=15000) # Wait for network to be idle
            
            search_result_div_selector = '#search' # Standard Google search results container
            try:
                search_result_div = await self.page.wait_for_selector(
                    search_result_div_selector, 
                    state="visible", 
                    timeout=10000
                )
            except Exception as e_selector: # More specific Playwright timeout error is better
                logger.warning(f"Could not find primary search result selector '{search_result_div_selector}'. "
                               f"Falling back to page content. Error: {e_selector}")
                # Fallback or alternative selectors can be tried here if #search fails
                # For now, just log and proceed to get full content if selector fails
                page_html_content = await self.page.content()
            else:
                # Give a brief moment for dynamic content within #search to settle if needed
                await asyncio.sleep(1) # Reduced sleep, networkidle should handle most.
                page_html_content = await search_result_div.inner_html()

            cleaned_search_result = clean(page_html_content, mode=self.cleaning_mode)
            
            return f'''here is the google search result html
<GoogleSearchResultStart>
{cleaned_search_result}
</GoogleSearchResultEnd>
'''
        except Exception as e:
            logger.error(f"Error during Google search for query '{query}': {e}", exc_info=True)
            # Propagate the error to be handled by BaseTool or agent
            raise RuntimeError(f"GoogleSearch failed for query '{query}': {str(e)}")
        finally:
            await self.close() # Close Playwright page/context from UIIntegrator

