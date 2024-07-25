from typing import List
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.social_media_poster.weibo.repositories.reviewed_movie_repository import ReviewedMovieModel, ReviewedMovieRepository

class ReviewedMoviesRetriever(BaseTool):
    def tool_usage(self):
        return 'ReviewedMoviesRetriever: Retrieves a list of previously reviewed movies. Usage: <<<ReviewedMoviesRetriever()>>>'

    def tool_usage_xml(self):
        return '''ReviewedMoviesRetriever: Retrieves a list of previously reviewed movies. Usage:
    <command name="ReviewedMoviesRetriever">
    </command>
    Returns a list of movie titles.
    '''

    async def execute(self, **kwargs):
        movie_review_repository = ReviewedMovieRepository()
        reviewed_movies: List[ReviewedMovieModel] = movie_review_repository.find_all()
        movie_titles = [movie.movie_title for movie in reviewed_movies]
        return f"here is the list of movies which are already reviewed {movie_titles}, you have to be look really carefully, since this list is getting longer and longer, pick one which is not on the list. Perhaps you have to do another google search with a different topic name"


