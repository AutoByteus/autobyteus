from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.social_media_poster.xiaohongshu.reviewed_books_retriever import ReviewedBooksRetriever

class ReviewedBooksRetrieverFactory(ToolFactory):
    def create_tool(self) -> ReviewedBooksRetriever:
        return ReviewedBooksRetriever()