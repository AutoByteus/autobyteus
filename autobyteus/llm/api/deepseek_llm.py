import logging
import os
from typing import Optional, List, AsyncGenerator
from openai import OpenAI
from openai.types.completion_usage import CompletionUsage
from openai.types.chat import ChatCompletionChunk
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole
from autobyteus.llm.utils.image_payload_formatter import process_image
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

logger = logging.getLogger(__name__)

class DeepSeekLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            logger.error("DEEPSEEK_API_KEY environment variable is not set.")
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

        self.client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        logger.info("DeepSeek API key and base URL set successfully")

        # Provide defaults if not specified
        if model is None:
            model = LLMModel.deepseek_chat
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.max_tokens = 8000

    def _create_token_usage(self, usage_data: Optional[CompletionUsage]) -> Optional[TokenUsage]:
        """Convert usage data to TokenUsage format."""
        if not usage_data:
            return None
        
        return TokenUsage(
            prompt_tokens=usage_data.prompt_tokens,
            completion_tokens=usage_data.completion_tokens,
            total_tokens=usage_data.total_tokens
        )

    async def _send_user_message_to_llm(
        self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs
    ) -> CompleteResponse:
        """
        Sends a non-streaming request to the DeepSeek API.
        Supports optional reasoning content if provided in the response.
        """
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if image_urls:
            for image_url in image_urls:
                try:
                    image_content = process_image(image_url)
                    content.append(image_content)
                    logger.info(f"Processed image: {image_url}")
                except ValueError as e:
                    logger.error(f"Error processing image {image_url}: {str(e)}")
                    continue

        self.add_user_message(content)
        logger.debug(f"Prepared message content: {content}")

        try:
            logger.info("Sending request to DeepSeek API")
            response = self.client.chat.completions.create(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
            )
            full_message = response.choices.message

            # Extract reasoning_content if present
            reasoning = None
            if hasattr(full_message, "reasoning_content") and full_message.reasoning_content:
                reasoning = full_message.reasoning_content
            elif "reasoning_content" in full_message and full_message["reasoning_content"]:
                reasoning = full_message["reasoning_content"]

            # Extract main content
            main_content = ""
            if hasattr(full_message, "content") and full_message.content:
                main_content = full_message.content
            elif "content" in full_message and full_message["content"]:
                main_content = full_message["content"]
            
            self.add_assistant_message(main_content, reasoning_content=reasoning)

            token_usage = self._create_token_usage(response.usage)
            logger.info("Received response from DeepSeek API with usage data")
            
            return CompleteResponse(
                content=main_content,
                reasoning=reasoning,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in DeepSeek API request: {str(e)}")
            raise ValueError(f"Error in DeepSeek API request: {str(e)}")
    
    async def _stream_user_message_to_llm(
        self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        """
        Streams the response from the DeepSeek API.
        Yields reasoning and content in separate chunks.
        """
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if image_urls:
            for image_url in image_urls:
                try:
                    image_content = process_image(image_url)
                    content.append(image_content)
                    logger.info(f"Processed image for streaming: {image_url}")
                except ValueError as e:
                    logger.error(f"Error processing image for streaming {image_url}: {str(e)}")
                    continue

        self.add_user_message(content)
        logger.debug(f"Prepared streaming message content: {content}")

        # Initialize variables to track reasoning and main content
        accumulated_reasoning = ""
        accumulated_content = ""

        try:
            logger.info("Starting streaming request to DeepSeek API")
            stream = self.client.chat.completions.create(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
                stream=True,
                stream_options={"include_usage": True}
            )

            for chunk in stream:
                chunk: ChatCompletionChunk

                # Process reasoning tokens
                reasoning_chunk = getattr(chunk.choices.delta, "reasoning_content", None)
                if reasoning_chunk:
                    accumulated_reasoning += reasoning_chunk
                    yield ChunkResponse(
                        content="",
                        reasoning=reasoning_chunk
                    )

                # Process main content tokens
                main_token = chunk.choices.delta.content
                if main_token:
                    accumulated_content += main_token
                    yield ChunkResponse(
                        content=main_token,
                        reasoning=None
                    )

                # Yield token usage if available in the final chunk
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    token_usage = self._create_token_usage(chunk.usage)
                    yield ChunkResponse(
                        content="",
                        reasoning=None,
                        is_complete=True,
                        usage=token_usage
                    )
            
            # After streaming, add the fully accumulated assistant message to history
            self.add_assistant_message(accumulated_content, reasoning_content=accumulated_reasoning)
            logger.info("Completed streaming response from DeepSeek API")

        except Exception as e:
            logger.error(f"Error in DeepSeek API streaming: {str(e)}")
            raise ValueError(f"Error in DeepSeek API streaming: {str(e)}")
    
    async def cleanup(self):
        await super().cleanup()
