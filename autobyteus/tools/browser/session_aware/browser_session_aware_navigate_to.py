from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.tool_config import ToolConfig
from urllib.parse import urlparse
from typing import Optional, TYPE_CHECKING, Any
import logging

from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class BrowserSessionAwareNavigateTo(BrowserSessionAwareTool):
    """
    A session-aware tool for navigating to a specified website using a shared browser session.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        logger.debug("BrowserSessionAwareNavigateTo tool initialized.")

    @classmethod
    def get_name(cls) -> str:
        return "NavigateTo"

    @classmethod
    def get_description(cls) -> str:
        return ("Navigates the shared browser session to a specified URL. "
                "Returns a success or failure message based on navigation status.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="webpage_url",
            param_type=ParameterType.STRING,
            description="The fully qualified URL of the website to navigate to (e.g., 'https://example.com').",
            required=True
        ))
        return schema
    
    async def perform_action(self, shared_session: SharedBrowserSession, webpage_url: str) -> str:
        logger.info(f"BrowserSessionAwareNavigateTo performing action for URL: {webpage_url}")

        if not self._is_valid_url(webpage_url):
            raise ValueError(f"Invalid URL format: {webpage_url}. Must include scheme and netloc.")

        try:
            response = await shared_session.page.goto(webpage_url, wait_until="networkidle", timeout=60000)
            
            if response and response.ok:
                success_msg = f"The NavigateTo command to {webpage_url} is executed successfully."
                logger.info(success_msg)
                return success_msg
            else:
                status = response.status if response else "Unknown"
                failure_msg = f"The NavigationTo command to {webpage_url} failed with status {status}."
                logger.warning(failure_msg)
                return failure_msg
        except Exception as e:
            logger.error(f"Error during shared session navigation to '{webpage_url}': {e}", exc_info=True)
            return f"Error navigating to {webpage_url}: {str(e)}"


    @staticmethod
    def _is_valid_url(url_string: str) -> bool:
        try:
            result = urlparse(url_string)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False
