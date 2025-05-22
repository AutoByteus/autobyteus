# File: autobyteus/tools/browser/session_aware/browser_session_aware_tool.py
from typing import TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.browser.session_aware.shared_browser_session_manager import SharedBrowserSessionManager
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession # Added for perform_action type hint

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext


class BrowserSessionAwareTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.shared_browser_session_manager = SharedBrowserSessionManager()
        # self.current_agent_context: Optional['AgentContext'] = None # Store context if needed by perform_action

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        # self.current_agent_context = context # Optionally store context
        shared_session = self.shared_browser_session_manager.get_shared_browser_session()
        
        if not shared_session:
            webpage_url = kwargs.get('webpage_url')
            if not webpage_url:
                raise ValueError("The 'webpage_url' keyword argument must be specified when creating a new shared session.")
            
            await self.shared_browser_session_manager.create_shared_browser_session()
            shared_session = self.shared_browser_session_manager.get_shared_browser_session()
            # Ensure page navigation happens after session is confirmed to be ready
            if shared_session and shared_session.page:
                 await shared_session.page.goto(webpage_url) # Consider wait_until options
            else:
                raise RuntimeError("Failed to create or retrieve a valid shared browser session page.")

            self.emit("shared_browser_session_created", shared_session) # Assuming 'emit' is defined in BaseTool or an ancestor
        
        return await self.perform_action(shared_session, **kwargs)

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement this method")
