import pytest
from autobyteus.tools.social_media_poster.weibo.repositories.reviewed_movie_repository import ReviewedMovieModel, ReviewedMovieRepository
from autobyteus.tools.social_media_poster.weibo.reviewed_movies_retriever import ReviewedMoviesRetriever

@pytest.fixture
def reviewed_movie_repository(mongo_database):
    yield ReviewedMovieRepository()
    mongo_database[ReviewedMovieModel.__collection_name__].drop()

@pytest.mark.asyncio
async def test_reviewed_movies_retriever(reviewed_movie_repository):
    # Create some reviewed movies
    movie1 = ReviewedMovieModel(movie_title="The Matrix", content="A groundbreaking sci-fi action film.")
    movie2 = ReviewedMovieModel(movie_title="Inception", content="A mind-bending thriller.")
    movie3 = ReviewedMovieModel(movie_title="The Shawshank Redemption", content="A powerful and uplifting prison drama.")

    reviewed_movie_repository.create(movie1)
    reviewed_movie_repository.create(movie2)
    reviewed_movie_repository.create(movie3)

    # Create an instance of ReviewedMoviesRetriever
    retriever = ReviewedMoviesRetriever()

    # Call the execute method to retrieve the reviewed movies
    result = await retriever.execute()

    # Verify the retrieved movie titles
    assert len(result) == 3
    assert "The Matrix" in result
    assert "Inception" in result
    assert "The Shawshank Redemption" in result


@pytest.mark.asyncio
async def test_reviewed_movies_retriever(reviewed_movie_repository):
    # Create an instance of ReviewedMoviesRetriever
    retriever = ReviewedMoviesRetriever()

    # Call the execute method to retrieve the reviewed movies
    result = await retriever.execute()
    print(result)
