from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from urllib.parse import urlparse

class BrowserSessionAwareNavigateTo(BrowserSessionAwareTool):
    """
    A session-aware tool for navigating to a specified website using a shared browser session.
    """

    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "NavigateTo"

    def tool_usage(self):
        return "NavigateTo: Navigates to a specified website. Usage: <<<NavigateTo(webpage_url='https://example.com')>>>, where 'https://example.com' is the URL of the website to navigate to."

    def tool_usage_xml(self):
        return '''
        NavigateTo: Navigates to a specified website. Usage:
        <command name="NavigateTo">
            <arg name="webpage_url">https://example.com</arg>
        </command>
        where "https://example.com" is the URL of the website to navigate to.
        '''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        """
        Navigate to the specified URL using the shared browser session.

        Args:
            shared_session (SharedBrowserSession): The shared browser session to use for navigation.
            **kwargs: Keyword arguments containing the URL. The URL should be specified as 'webpage_url'.

        Returns:
            str: A message indicating successful navigation or an error message.

        Raises:
            ValueError: If the 'webpage_url' keyword argument is not specified or is invalid.
        """
        webpage_url = kwargs.get('webpage_url')
        if not webpage_url:
            raise ValueError("The 'webpage_url' keyword argument must be specified.")

        if not self._is_valid_url(webpage_url):
            raise ValueError(f"Invalid URL: {webpage_url}")

        response = await shared_session.page.goto(webpage_url, wait_until="networkidle")
        if response.ok:
            return f"The NavigateTo command to {webpage_url} is executed"
        else:
            return f"The NavigationTo command to {webpage_url} failed with status {response.status}"

    @staticmethod
    def _is_valid_url(url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False