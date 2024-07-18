import pytest
from autobyteus.tools.weibo.repositories.reviewed_movie_repository import ReviewedMovieModel, ReviewedMovieRepository

@pytest.fixture
def reviewed_movie_repository(mongo_database):
    yield ReviewedMovieRepository()
    mongo_database[ReviewedMovieModel.__collection_name__].drop()

def test_create_and_find_reviewed_movie(reviewed_movie_repository):
    movie_title = "The Matrix"
    content = "A groundbreaking sci-fi action film."

    reviewed_movie = ReviewedMovieModel(movie_title=movie_title, content=content)
    reviewed_movie_repository.create(reviewed_movie)

    retrieved_movies = reviewed_movie_repository.find_by_attributes({"movie_title": movie_title})
    assert len(retrieved_movies) == 1
    retrieved_movie = retrieved_movies[0]
    assert retrieved_movie.movie_title == movie_title
    assert retrieved_movie.content == content
    assert retrieved_movie.review_id is not None
    assert retrieved_movie.timestamp is not None

def test_find_all_reviewed_movies(reviewed_movie_repository):
    movie1 = ReviewedMovieModel(movie_title="The Matrix", content="A groundbreaking sci-fi action film.")
    movie2 = ReviewedMovieModel(movie_title="Inception", content="A mind-bending thriller.")

    reviewed_movie_repository.create(movie1)
    reviewed_movie_repository.create(movie2)

    reviewed_movies = reviewed_movie_repository.find_all()
    assert len(reviewed_movies) == 2
    assert any(movie.movie_title == "The Matrix" for movie in reviewed_movies)
    assert any(movie.movie_title == "Inception" for movie in reviewed_movies)

def test_find_reviewed_movies_by_attributes(reviewed_movie_repository):
    movie1 = ReviewedMovieModel(movie_title="The Matrix", content="A groundbreaking sci-fi action film.")
    movie2 = ReviewedMovieModel(movie_title="The Matrix Reloaded", content="The second installment in The Matrix trilogy.")

    reviewed_movie_repository.create(movie1)
    reviewed_movie_repository.create(movie2)

    reviewed_movies = reviewed_movie_repository.find_by_attributes({"movie_title": {"$regex": "^The Matrix"}})
    assert len(reviewed_movies) == 2
    assert all(movie.movie_title.startswith("The Matrix") for movie in reviewed_movies)