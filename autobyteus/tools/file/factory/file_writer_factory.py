from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.file.file_writer import FileWriter

class FileWriterFactory(ToolFactory):
    def create_tool(self) -> FileWriter:
        return FileWriter()