from enum import Enum
import os
from urllib.parse import urlparse

class ContextFileType(str, Enum):
    """
    Enumerates the types of context files that can be provided to an agent.
    """
    TEXT = "text"          # .txt, .md (if treated as plain text initially)
    MARKDOWN = "markdown"  # .md (if specific markdown processing is intended)
    PDF = "pdf"            # .pdf
    DOCX = "docx"          # .docx (Microsoft Word)
    PPTX = "pptx"          # .pptx (Microsoft PowerPoint)
    XLSX = "xlsx"          # .xlsx (Microsoft Excel)
    CSV = "csv"            # .csv
    JSON = "json"          # .json
    XML = "xml"            # .xml
    HTML = "html"          # .html, .htm
    PYTHON = "python"      # .py
    JAVASCRIPT = "javascript" # .js
    AUDIO = "audio"        # .mp3, .wav, .m4a, .flac, .ogg
    VIDEO = "video"        # .mp4, .mov, .avi, .mkv, .webm
    IMAGE = "image"        # .png, .jpg, .jpeg, .gif, .webp (when image is for contextual analysis, not direct LLM vision input)
    UNKNOWN = "unknown"    # Fallback for unrecognized types

    @classmethod
    def from_path(cls, uri: str) -> 'ContextFileType':
        """
        Infers the ContextFileType from a file path or URL based on its extension.
        """
        if not uri or not isinstance(uri, str):
            return cls.UNKNOWN

        try:
            # Parse the URI to handle both file paths and URLs gracefully
            parsed_path = urlparse(uri).path
            _, extension = os.path.splitext(parsed_path.lower())
        except Exception:
            # Fallback for malformed URIs
            _, extension = os.path.splitext(uri.lower())

        if extension == ".txt":
            return cls.TEXT
        elif extension == ".md":
            return cls.MARKDOWN
        elif extension == ".pdf":
            return cls.PDF
        elif extension == ".docx":
            return cls.DOCX
        elif extension == ".pptx":
            return cls.PPTX
        elif extension == ".xlsx":
            return cls.XLSX
        elif extension == ".csv":
            return cls.CSV
        elif extension == ".json":
            return cls.JSON
        elif extension == ".xml":
            return cls.XML
        elif extension in [".html", ".htm"]:
            return cls.HTML
        elif extension == ".py":
            return cls.PYTHON
        elif extension == ".js":
            return cls.JAVASCRIPT
        elif extension in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
            return cls.AUDIO
        elif extension in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            return cls.VIDEO
        elif extension in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
            return cls.IMAGE
        else:
            return cls.UNKNOWN

    @classmethod
    def get_readable_text_types(cls) -> list['ContextFileType']:
        """Returns a list of file types that can be read as plain text for context."""
        return [
            cls.TEXT,
            cls.MARKDOWN,
            cls.JSON,
            cls.XML,
            cls.HTML,
            cls.PYTHON,
            cls.JAVASCRIPT,
            cls.CSV,
        ]

    def __str__(self) -> str:
        return self.value
