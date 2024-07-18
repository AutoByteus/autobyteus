from repository_mongodb import BaseModel, BaseRepository
from bson import ObjectId
from datetime import datetime

class ReviewedMovieModel(BaseModel):
    __collection_name__ = "reviewed_movies"

    review_id: ObjectId = ObjectId()
    movie_title: str
    content: str
    timestamp: datetime = datetime.utcnow()

class ReviewedMovieRepository(BaseRepository[ReviewedMovieModel]):
    pass