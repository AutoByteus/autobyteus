from typing import List
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.weibo.repositories.reviewed_movie_repository import ReviewedMovieModel, ReviewedMovieRepository

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
        return movie_titles