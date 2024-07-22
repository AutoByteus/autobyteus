from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.browser.session_aware.shared_browser_session_manager import SharedBrowserSessionManager

class BrowserSessionAwareTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.shared_browser_session_manager = SharedBrowserSessionManager()

    def set_shared_browser_session(self, shared_session):
        self.shared_browser_session_manager.set_shared_browser_session(shared_session)

    def get_shared_browser_session(self):
        return self.shared_browser_session_manager.get_shared_browser_session()