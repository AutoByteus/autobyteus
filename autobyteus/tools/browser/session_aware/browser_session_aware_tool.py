from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.browser.session_aware.shared_browser_session_manager import SharedBrowserSessionManager

class BrowserSessionAwareTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.shared_browser_session_manager = SharedBrowserSessionManager()

    async def get_or_create_shared_browser_session(self):
        shared_session = self.shared_browser_session_manager.get_shared_browser_session()
        if not shared_session:
            await self.shared_browser_session_manager.create_shared_browser_session()
            shared_session = self.shared_browser_session_manager.get_shared_browser_session()
            self.emit("shared_browser_session_created", shared_session)
        return shared_session