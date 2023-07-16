from typing import Optional

class FileRecord:
    """
    A class used to store metadata and contents of a file.

    Attributes
    ----------
    path : str
        The full path of the file.
    size : int
        The size of the file in bytes.
    creation_time : str
        The creation time of the file.
    content : str, optional
        The content of the file.
    """

    def __init__(self, path: str, size: int, creation_time: str, content: Optional[str] = None):
        self.path = path
        self.size = size
        self.creation_time = creation_time
        self.content = content
