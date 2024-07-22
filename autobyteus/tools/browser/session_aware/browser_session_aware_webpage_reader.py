from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.utils.html_cleaner import clean

class BrowserSessionAwareWebPageReader(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

    def tool_usage(self):
        return 'WebPageReader: Reads and cleans the HTML content from a given webpage. Usage: <<<WebPageReader(url="webpage_url")>>>, where "webpage_url" is a string containing the URL of the webpage to read the content from.'

    def tool_usage_xml(self):
        return '''WebPageReader: Reads the HTML content from a given webpage. Usage:
<command name="WebPageReader">
  <arg name="url">webpage_url</arg>
</command>
where "webpage_url" is a string containing the URL of the webpage to read the content from.
'''

    async def execute(self, **kwargs):
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        shared_session = self.get_shared_browser_session()
        if not shared_session:
            self.emit("create_shared_session")
            shared_session = self.get_shared_browser_session()

        await shared_session.page.goto(url)
        page_content = await shared_session.page.content()
        cleaned_content = clean(page_content, lite=True)
        return cleaned_content