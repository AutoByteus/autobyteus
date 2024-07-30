from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.social_media_poster.xiaohongshu.xiaohongshu_poster import XiaohongshuPoster

class XiaohongshuPosterFactory(ToolFactory):
    def __init__(self, xiaohongshu_account_name: str):
        self.xiaohongshu_account_name = xiaohongshu_account_name

    def create_tool(self) -> XiaohongshuPoster:
        return XiaohongshuPoster(self.xiaohongshu_account_name)