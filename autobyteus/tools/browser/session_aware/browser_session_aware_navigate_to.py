from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from urllib.parse import urlparse
from typing import Optional, TYPE_CHECKING, Any # Added
import logging # Added

from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Added

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Not directly used by this tool's methods but good for consistency
    # perform_action does not take AgentContext, it's handled by BaseTool._execute

logger = logging.getLogger(__name__) # Added

class BrowserSessionAwareNavigateTo(BrowserSessionAwareTool):
    """
    A session-aware tool for navigating to a specified website using a shared browser session.
    """

    def __init__(self): # No instantiation config
        super().__init__()
        logger.debug("BrowserSessionAwareNavigateTo tool initialized.")

    # get_name() is inherited from BaseTool via BrowserSessionAwareTool, uses class name "BrowserSessionAwareNavigateTo"
    # If a different registered name like "NavigateTo" (session-aware) is desired, override get_name().
    # The original class name suggests it would register as "BrowserSessionAwareNavigateTo".
    # Let's assume the name from the context `NavigateTo` was desired.
    @classmethod
    def get_name(cls) -> str: # Overriding to match previous apparent name
        return "NavigateTo" # Was previously "NavigateTo" in its tool_usage_xml

    @classmethod
    def get_description(cls) -> str:
        return ("Navigates the shared browser session to a specified URL. "
                "Returns a success or failure message based on navigation status.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="webpage_url", # Argument name used by perform_action and its callers
            param_type=ParameterType.STRING,
            description="The fully qualified URL of the website to navigate to (e.g., 'https://example.com').",
            required=True
        ))
        return schema
    
    # get_config_schema() defaults to None (no instantiation config)
    # tool_usage_xml() is inherited from BaseTool and generated

    # This method is called by BrowserSessionAwareTool._execute
    async def perform_action(self, shared_session: SharedBrowserSession, webpage_url: str) -> str: # Named parameter
        """
        Navigate to the specified URL using the shared browser session.
        'webpage_url' is validated by BaseTool.execute against get_argument_schema().
        """
        logger.info(f"BrowserSessionAwareNavigateTo performing action for URL: {webpage_url}")

        if not self._is_valid_url(webpage_url): # Specific validation for URL format
            # This error should ideally be caught by schema validation if pattern is used.
            # If not, raising ValueError here is okay.
            raise ValueError(f"Invalid URL format: {webpage_url}. Must include scheme and netloc.")

        # Playwright's goto can raise TimeoutError if navigation takes too long.
        # Handle common Playwright errors if necessary, or let them propagate.
        try:
            response = await shared_session.page.goto(webpage_url, wait_until="networkidle", timeout=60000)
            
            if response and response.ok: # Check response explicitly
                success_msg = f"The NavigateTo command to {webpage_url} is executed successfully."
                logger.info(success_msg)
                return success_msg
            else:
                status = response.status if response else "Unknown"
                failure_msg = f"The NavigationTo command to {webpage_url} failed with status {status}."
                logger.warning(failure_msg)
                return failure_msg # Return failure message
        except Exception as e: # Catch Playwright errors (e.g., TimeoutError, NetworkError)
            logger.error(f"Error during shared session navigation to '{webpage_url}': {e}", exc_info=True)
            # Return an error message, or re-raise a more specific/tool-related error
            return f"Error navigating to {webpage_url}: {str(e)}"


    @staticmethod
    def _is_valid_url(url_string: str) -> bool: # Added type hint
        try:
            result = urlparse(url_string)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

