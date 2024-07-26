from repository_mongodb import BaseModel, BaseRepository
from bson import ObjectId
from datetime import datetime

class XiaohongshuBookReviewModel(BaseModel):
    __collection_name__ = "xiaohongshu_book_reviews"

    review_id: ObjectId = ObjectId()
    title: str
    content: str
    timestamp: datetime = datetime.utcnow()

class XiaohongshuBookReviewRepository(BaseRepository[XiaohongshuBookReviewModel]):
    pass