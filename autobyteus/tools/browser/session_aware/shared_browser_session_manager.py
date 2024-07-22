from autobyteus.utils.singleton import SingletonMeta
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.events.event_emitter import EventEmitter

class SharedBrowserSessionManager(metaclass=SingletonMeta):
    def __init__(self):
        self.shared_browser_session = None
        self.event_emitter = EventEmitter()
        self.event_emitter.subscribe("create_shared_session", self.create_shared_browser_session)

    async def create_shared_browser_session(self):
        self.shared_browser_session = SharedBrowserSession()
        await self.shared_browser_session.initialize()

    async def close_shared_browser_session(self):
        if self.shared_browser_session:
            await self.shared_browser_session.close()
            self.shared_browser_session = None

    def set_shared_browser_session(self, shared_session):
        self.shared_browser_session = shared_session

    def get_shared_browser_session(self):
        return self.shared_browser_session