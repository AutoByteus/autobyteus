from typing import List, Optional

class UserMessage:
    def __init__(self, content: str, file_paths: Optional[List[str]] = None):
        self.content = content
        self.file_paths = file_paths or []

    def __str__(self):
        return f"UserMessage(content={self.content}, file_paths={self.file_paths})"