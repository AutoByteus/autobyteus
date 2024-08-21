# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_screenshot_taker.py

import os
from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession

class BrowserSessionAwareWebPageScreenshotTaker(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "WebPageScreenshotTaker"

    def tool_usage(self):
        return "WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file. Usage: <<<WebPageScreenshotTaker(webpage_url='url_to_screenshot', file_name='screenshot_file_name')>>>, where 'url_to_screenshot' is a string containing the URL of the webpage to take a screenshot of, and 'screenshot_file_name' is the name of the file to save the screenshot (including extension, e.g., 'screenshot.png'). Optionally, 'screenshot_file_name' can include a relative path (e.g., 'images/screenshot.png'). Returns the absolute file path of the saved screenshot."

    def tool_usage_xml(self):
        return '''WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file. Usage:
<command name="WebPageScreenshotTaker">
  <arg name="webpage_url">url_to_screenshot</arg>
  <arg name="file_name">screenshot_file_name</arg>
</command>
where "url_to_screenshot" is a string containing the URL of the webpage to take a screenshot of, and "screenshot_file_name" is the name of the file to save the screenshot (including extension, e.g., 'screenshot.png'). Optionally, "screenshot_file_name" can include a relative path (e.g., 'images/screenshot.png').
Returns the absolute file path of the saved screenshot.
'''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        file_name = kwargs.get('file_name')
        if not file_name:
            raise ValueError("The 'file_name' keyword argument must be specified.")

        await shared_session.page.screenshot(path=file_name, full_page=True)
        absolute_path = os.path.abspath(file_name)
        return absolute_path