from enum import Enum
import os

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
    IMAGE = "image"        # .png, .jpg, .jpeg, .gif, .webp (when image is for contextual analysis, not direct LLM vision input)
    UNKNOWN = "unknown"    # Fallback for unrecognized types

    @classmethod
    def from_path(cls, file_path: str) -> 'ContextFileType':
        """
        Infers the ContextFileType from a file path based on its extension.
        """
        if not file_path or not isinstance(file_path, str):
            return cls.UNKNOWN
        
        _, extension = os.path.splitext(file_path.lower())
        
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
        elif extension in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
            return cls.IMAGE 
        else:
            return cls.UNKNOWN

    def __str__(self) -> str:
        return self.value
