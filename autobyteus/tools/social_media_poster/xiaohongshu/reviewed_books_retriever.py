# File: autobyteus/tools/social_media_poster/xiaohongshu/reviewed_books_retriever.py

from typing import List
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.social_media_poster.xiaohongshu.repositories.book_review_repository import XiaohongshuBookReviewModel, ReviewedBooksRepository as BookReviewRepository

class ReviewedBooksRetriever(BaseTool):
    def tool_usage(self) -> str:
        return 'ReviewedBooksRetriever: Retrieves a list of previously reviewed books on Xiaohongshu. Usage: <<<ReviewedBooksRetriever()>>>'

    def tool_usage_xml(self) -> str:
        return '''ReviewedBooksRetriever: Retrieves a list of previously reviewed books on Xiaohongshu. Usage:
    <command name="ReviewedBooksRetriever">
    </command>
    Returns a list of book titles.
    '''

    async def _execute(self, **kwargs) -> str:
        book_review_repository = BookReviewRepository()
        reviewed_books: List[XiaohongshuBookReviewModel] = book_review_repository.find_all()
        book_titles = [f"{book.original_title} ({book.title})" for book in reviewed_books]
        
        return (f"Here is the list of books which have already been reviewed on Xiaohongshu: {book_titles}. "
                "Please examine this list carefully, as it continues to grow. "
                "Choose a book that is not on this list for your next review. "
                "You may need to perform another search to find a suitable book topic.")