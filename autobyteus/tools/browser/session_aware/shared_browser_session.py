from brui_core.ui_integrator import UIIntegrator

class SharedBrowserSession(UIIntegrator):
    def __init__(self):
        super().__init__()

    async def initialize(self):
        await super().initialize()

    async def close(self):
        await super().close(close_page=False, close_context=False, close_browser=False)