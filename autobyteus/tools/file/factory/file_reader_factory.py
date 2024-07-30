from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.file.file_reader import FileReader

class FileReaderFactory(ToolFactory):
    def create_tool(self) -> FileReader:
        return FileReader()