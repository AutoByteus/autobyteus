# file: autobyteus/autobyteus/agent/message/multimodal_message_builder.py
import logging

from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.context_file_type import ContextFileType
from autobyteus.llm.user_message import LLMUserMessage

logger = logging.getLogger(__name__)

def build_llm_user_message(agent_input_user_message: AgentInputUserMessage) -> LLMUserMessage:
    """
    Builds an LLMUserMessage from an AgentInputUserMessage by categorizing its context files.

    This function iterates through the context files, sorting URIs for images, audio, and video
    into the appropriate fields of the LLMUserMessage. It ignores other file types for now.

    Args:
        agent_input_user_message: The user input message containing content and context files.

    Returns:
        An LLMUserMessage ready to be sent to the LLM.
    """
    image_urls = []
    audio_urls = []
    video_urls = []

    if agent_input_user_message.context_files:
        for context_file in agent_input_user_message.context_files:
            file_type = context_file.file_type
            if file_type == ContextFileType.IMAGE:
                image_urls.append(context_file.uri)
            elif file_type == ContextFileType.AUDIO:
                audio_urls.append(context_file.uri)
            elif file_type == ContextFileType.VIDEO:
                video_urls.append(context_file.uri)
            else:
                logger.debug(f"Ignoring non-media context file of type '{file_type.value}' during LLM message build: {context_file.uri}")

    llm_user_message = LLMUserMessage(
        content=agent_input_user_message.content,
        image_urls=image_urls if image_urls else None,
        audio_urls=audio_urls if audio_urls else None,
        video_urls=video_urls if video_urls else None
    )

    logger.info(f"Built LLMUserMessage with {len(image_urls)} images, {len(audio_urls)} audio, {len(video_urls)} video files.")
    return llm_user_message
