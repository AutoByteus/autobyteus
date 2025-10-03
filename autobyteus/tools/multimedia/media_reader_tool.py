# file: autobyteus/autobyteus/tools/multimedia/media_reader_tool.py
import logging
import os
from typing import TYPE_CHECKING, Optional

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.message.context_file import ContextFile

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace

logger = logging.getLogger(__name__)

class ReadMediaFile(BaseTool):
    """
    A tool that loads a media file (image, audio, video) into the context for
    the next LLM turn. This allows a multimodal LLM to directly 'see' or 'hear'
    the file's content. The tool's result is a structured object that the system
    uses to construct a multimodal prompt, not plain text.
    """
    TOOL_NAME = "ReadMediaFile"
    CATEGORY = ToolCategory.MULTIMEDIA

    @classmethod
    def get_name(cls) -> str:
        return cls.TOOL_NAME

    @classmethod
    def get_description(cls) -> str:
        return (
            "Loads a media file (image, audio, video) into the context for the next turn, "
            "allowing the LLM to directly analyze its content. Use this when you need to 'see' an image, "
            "'listen' to audio, or 'watch' a video that you know exists in the workspace or file system."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="file_path",
            param_type=ParameterType.STRING,
            description="The absolute path or workspace-relative path to the media file.",
            required=True
        ))
        return schema

    async def _execute(self,
                       context: 'AgentContext',
                       file_path: str) -> 'ContextFile':
        """
        Resolves the file path and returns a ContextFile object, which signals
        the system to include this file in the next multimodal LLM prompt.
        It handles both absolute paths and paths relative to the agent's workspace.
        """
        logger.debug(f"Tool '{self.get_name()}': Received request to read media file at '{file_path}'.")
        
        absolute_path: str
        workspace: Optional['BaseAgentWorkspace'] = context.workspace

        if os.path.isabs(file_path):
            absolute_path = os.path.normpath(file_path)
            logger.debug(f"Path '{file_path}' is absolute. Using resolved path: '{absolute_path}'.")
            
            # Security Note: This allows reading from outside the workspace.
            # We log a warning if this occurs.
            if workspace and hasattr(workspace, 'get_base_path'):
                try:
                    workspace_root = os.path.abspath(workspace.get_base_path())
                    resolved_target = os.path.abspath(absolute_path)
                    if not os.path.commonpath([workspace_root]) == os.path.commonpath([workspace_root, resolved_target]):
                        logger.warning(
                            f"Security Note: Tool '{self.get_name()}' is accessing an absolute path "
                            f"'{absolute_path}' which is outside the agent's workspace '{workspace_root}'."
                        )
                except Exception:
                    # Failsafe if get_base_path has an issue.
                    pass
        else:
            # Handle relative paths, which MUST be resolved against a workspace that supports file paths.
            if not (workspace and hasattr(workspace, 'get_base_path') and callable(getattr(workspace, 'get_base_path'))):
                raise ValueError(
                    f"A relative path '{file_path}' was provided, but the agent's workspace does not support "
                    "file system path resolution. Please provide an absolute path or configure a suitable workspace."
                )

            try:
                base_path = os.path.abspath(workspace.get_base_path())
                # Securely join the path and resolve it to a final absolute path
                absolute_path = os.path.abspath(os.path.join(base_path, file_path))
                
                # Security Check: Ensure the resolved path is still within the workspace directory.
                if os.path.commonpath([base_path]) != os.path.commonpath([base_path, absolute_path]):
                    raise ValueError(f"Security error: Path '{file_path}' attempts to access files outside the agent's workspace.")
                
                logger.debug(f"Path '{file_path}' is relative. Resolved against workspace to '{absolute_path}'.")

            except ValueError as e:
                # Re-raise security errors with more context.
                logger.error(f"Tool '{self.get_name()}': Security error resolving relative path '{file_path}': {e}")
                raise

        try:
            if not os.path.exists(absolute_path) or not os.path.isfile(absolute_path):
                raise FileNotFoundError(f"The file '{file_path}' does not exist or is not a regular file at the resolved path '{absolute_path}'.")
            
            logger.info(f"Tool '{self.get_name()}': Staging file '{absolute_path}' for next LLM turn.")
            
            # The ContextFile constructor will automatically infer file_type from the path.
            # This is the special object that the ToolResultEventHandler will look for.
            return ContextFile(uri=absolute_path)

        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Tool '{self.get_name()}': Error processing path '{file_path}': {e}")
            raise
