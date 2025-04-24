# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_reader.py

from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.utils.html_cleaner import clean, CleaningMode

class BrowserSessionAwareWebPageReader(BrowserSessionAwareTool):
    def __init__(self, cleaning_mode=CleaningMode.THOROUGH):
        super().__init__()
        self.cleaning_mode = cleaning_mode

    def get_name(self) -> str:
        return "WebPageReader"

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the WebPageReader tool.

        Returns:
            str: An XML description of how to use the WebPageReader tool.
        """
        return '''WebPageReader: Reads and cleans the HTML content from a given webpage. Usage:
<command name="WebPageReader">
  <arg name="webpage_url">url_to_read</arg>
</command>
where "url_to_read" is a string containing the URL of the webpage to read the content from.
'''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        page_content = await shared_session.page.content()
        cleaned_content = clean(page_content, self.cleaning_mode)
        return cleaned_content
