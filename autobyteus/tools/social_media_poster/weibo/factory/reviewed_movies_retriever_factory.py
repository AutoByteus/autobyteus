from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.social_media_poster.weibo.reviewed_movies_retriever import ReviewedMoviesRetriever

class ReviewedMoviesRetrieverFactory(ToolFactory):
    def create_tool(self) -> ReviewedMoviesRetriever:
        return ReviewedMoviesRetriever()