import asyncio
from typing import Dict
from bson import ObjectId
from autobyteus.tools.social_media_poster.weibo.repositories.reviewed_movie_repository import ReviewedMovieRepository, ReviewedMovieModel

# Translation dictionary. We use this script to update the movie title.
TRANSLATIONS: Dict[str, str] = {
    '死亡诗社': 'Dead Poets Society',
    '隐藏人物': 'Hidden Figures',
    '淑女鸟': 'Lady Bird',
    '紫色（2023）': 'The Color Purple (2023)',
    '小妇人 (Little Women)': 'Little Women',
    '艾琳·布洛克维奇': 'Erin Brockovich',
    '律政俏佳人': 'Legally Blonde',
    '自由作家': 'Freedom Writers',
    'Good Will Hunting': 'Good Will Hunting'
}

async def translate_movie_titles():
    repository = ReviewedMovieRepository()
    movies = repository.find_all()

    for movie in movies:
        if movie.movie_title in TRANSLATIONS:
            english_title = TRANSLATIONS[movie.movie_title]
            if english_title != movie.movie_title:
                print(f"Translating: {movie.movie_title} -> {english_title}")
                movie.movie_title = english_title
                repository.update(movie)
            else:
                print(f"Already in English: {movie.movie_title}")
        else:
            print(f"No translation found for: {movie.movie_title}")

if __name__ == "__main__":
    asyncio.run(translate_movie_titles())