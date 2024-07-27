# File: tests/integration_tests/tools/xiaohongshu/test_reviewed_books_retriever.py
import pytest
from bson import ObjectId
from datetime import datetime

from autobyteus.tools.social_media_poster.xiaohongshu.repositories.book_review_repository import XiaohongshuBookReviewModel, ReviewedBooksRepository

@pytest.fixture
def reviewed_books_retriever(mongo_database):
    yield ReviewedBooksRepository()
    mongo_database[XiaohongshuBookReviewModel.__collection_name__].drop()

def test_create_and_find_book_review(reviewed_books_retriever):
    original_title = "Pride and Prejudice"
    title = "傲慢与偏见"
    content = "简·奥斯汀的经典小说，探讨了爱情、婚姻和社会阶级。"

    book_review = XiaohongshuBookReviewModel(
        original_title=original_title,
        title=title,
        content=content
    )
    reviewed_books_retriever.create(book_review)

    retrieved_reviews = reviewed_books_retriever.find_by_attributes({"original_title": original_title})
    assert len(retrieved_reviews) == 1
    retrieved_review = retrieved_reviews[0]
    assert retrieved_review.original_title == original_title
    assert retrieved_review.title == title
    assert retrieved_review.content == content
    assert isinstance(retrieved_review.review_id, ObjectId)
    assert isinstance(retrieved_review.timestamp, datetime)

def test_find_all_book_reviews(reviewed_books_retriever):
    review1 = XiaohongshuBookReviewModel(
        original_title="1984",
        title="一九八四",
        content="乔治·奥威尔的反乌托邦小说，描绘了一个极权主义社会。"
    )
    review2 = XiaohongshuBookReviewModel(
        original_title="To Kill a Mockingbird",
        title="杀死一只知更鸟",
        content="哈珀·李的成长小说，讲述了种族歧视和正义的主题。"
    )

    reviewed_books_retriever.create(review1)
    reviewed_books_retriever.create(review2)

    retrieved_reviews = reviewed_books_retriever.find_all()
    assert len(retrieved_reviews) == 2
    assert any(review.original_title == "1984" for review in retrieved_reviews)
    assert any(review.original_title == "To Kill a Mockingbird" for review in retrieved_reviews)

def test_find_book_reviews_by_attributes(reviewed_books_retriever):
    review1 = XiaohongshuBookReviewModel(
        original_title="The Great Gatsby",
        title="了不起的盖茨比",
        content="菲茨杰拉德的经典小说，描绘了爵士时代的美国梦。"
    )
    review2 = XiaohongshuBookReviewModel(
        original_title="The Catcher in the Rye",
        title="麦田里的守望者",
        content="塞林格的叛逆青春小说，探讨了青少年的成长困惑。"
    )

    reviewed_books_retriever.create(review1)
    reviewed_books_retriever.create(review2)

    retrieved_reviews = reviewed_books_retriever.find_by_attributes({"original_title": {"$regex": "^The"}})
    assert len(retrieved_reviews) == 2
    assert all(review.original_title.startswith("The") for review in retrieved_reviews)