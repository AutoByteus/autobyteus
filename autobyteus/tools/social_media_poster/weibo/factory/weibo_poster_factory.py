from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.social_media_poster.weibo.weibo_poster import WeiboPoster

class WeiboPosterFactory(ToolFactory):
    def __init__(self, weibo_account_name: str):
        self.weibo_account_name = weibo_account_name

    def create_tool(self) -> WeiboPoster:
        return WeiboPoster(self.weibo_account_name)