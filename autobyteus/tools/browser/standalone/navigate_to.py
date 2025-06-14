from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from brui_core.ui_integrator import UIIntegrator
from urllib.parse import urlparse
from typing import Optional, TYPE_CHECKING, Any
import logging

from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class NavigateTo(BaseTool, UIIntegrator):
    """
    A standalone tool for navigating to a specified website using Playwright.
    It initializes and closes its own browser instance for each navigation.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self, config=config)
        UIIntegrator.__init__(self)
        logger.debug("NavigateTo (standalone) tool initialized.")

    @classmethod
    def get_description(cls) -> str:
        return "Navigates a standalone browser instance to a specified URL. Returns a success or failure message."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url",
            param_type=ParameterType.STRING,
            description="The fully qualified URL of the website to navigate to (e.g., 'https://example.com').",
            required=True
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str) -> str:
        logger.info(f"NavigateTo (standalone) for agent {context.agent_id} navigating to: {url}")

        if not self._is_valid_url(url):
            error_msg = f"Invalid URL format: {url}. Must include scheme (e.g., http, https) and netloc."
            logger.warning(f"NavigateTo (standalone) validation error for agent {context.agent_id}: {error_msg}")
            raise ValueError(error_msg)

        try:
            await self.initialize()
            if not self.page:
                 logger.error("Playwright page not initialized in NavigateTo (standalone).")
                 raise RuntimeError("Playwright page not available for NavigateTo.")

            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=60000) 
            
            if response and response.ok:
                success_msg = f"Successfully navigated to {url}"
                logger.info(f"NavigateTo (standalone) for agent {context.agent_id}: {success_msg}")
                return success_msg
            else:
                status = response.status if response else "Unknown"
                failure_msg = f"Navigation to {url} failed with status {status}"
                logger.warning(f"NavigateTo (standalone) for agent {context.agent_id}: {failure_msg}")
                return failure_msg
        except Exception as e:
            logger.error(f"Error during NavigateTo (standalone) for URL '{url}', agent {context.agent_id}: {e}", exc_info=True)
            raise RuntimeError(f"NavigateTo (standalone) failed for URL '{url}': {str(e)}")
        finally:
            await self.close()

    @staticmethod
    def _is_valid_url(url_string: str) -> bool:
        try:
            result = urlparse(url_string)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False
