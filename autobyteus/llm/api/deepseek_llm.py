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
    def __init__(self, model: LLMModel = None, system_message: str = None, custom_config: LLMConfig = None):
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            logger.error("DEEPSEEK_API_KEY environment variable is not set.")
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

        self.client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        logger.info("DeepSeek API key and base URL set successfully")

        super().__init__(model=model or LLMModel.DEEPSEEK_CHAT_API, system_message=system_message, custom_config=custom_config)
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
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> CompleteResponse:
        """
        Sends a non-streaming request to the DeepSeek API.
        Supports optional reasoning content if provided in the response.
        """
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if file_paths:
            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)
                    content.append(image_content)
                    logger.info(f"Processed image: {file_path}")
                except ValueError as e:
                    logger.error(f"Error processing image {file_path}: {str(e)}")
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
            full_message = response.choices[0].message

            # Extract reasoning_content if present
            if hasattr(full_message, "reasoning_content"):
                reasoning = full_message.reasoning_content or ""
            else:
                reasoning = full_message.get("reasoning_content", "")

            # Extract main content
            if hasattr(full_message, "content"):
                main_content = full_message.content or ""
            else:
                main_content = full_message.get("content", "")

            # Construct display content with delimiters if reasoning exists
            if reasoning:
                display_content = f"<llm_reasoning_token>{reasoning}</llm_reasoning_token>\n{main_content}"
                self.add_assistant_message(main_content, reasoning_content=reasoning)
            else:
                display_content = main_content
                self.add_assistant_message(main_content)

            token_usage = self._create_token_usage(response.usage)
            logger.info("Received response from DeepSeek API with usage data")
            
            return CompleteResponse(
                content=display_content,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in DeepSeek API request: {str(e)}")
            raise ValueError(f"Error in DeepSeek API request: {str(e)}")
    
    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        """
        Streams the response from the DeepSeek API.
        Supports optional reasoning content with immediate yielding.
        
        Streaming Behavior Adjustments:
        - Every reasoning chunk is yielded immediately.
        - For the very first reasoning chunk, prepend "<llm_reasoning_token>" to its content.
        - When the first main content token is encountered:
            - If any reasoning tokens have been yielded, immediately yield an extra chunk with "</llm_reasoning_token>\n"
              to mark the end of the reasoning section.
        - If no main content tokens are encountered (only reasoning), after streaming completes,
          yield a final chunk with "</llm_reasoning_token>\n" to close the reasoning section.
        - After streaming, add the assistant message with or without reasoning content as follows:
              if reasoning_content:
                  self.add_assistant_message(accumulated_content, reasoning_content=reasoning_content)
              else:
                  self.add_assistant_message(accumulated_content)
        """
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if file_paths:
            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)
                    content.append(image_content)
                    logger.info(f"Processed image for streaming: {file_path}")
                except ValueError as e:
                    logger.error(f"Error processing image for streaming {file_path}: {str(e)}")
                    continue

        self.add_user_message(content)
        logger.debug(f"Prepared streaming message content: {content}")

        # Initialize variables to track reasoning and main content
        reasoning_content = ""
        first_reasoning_emitted = False
        reasoning_closed = False
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

                # Process reasoning tokens: yield immediately and accumulate.
                reasoning_chunk = getattr(chunk.choices[0].delta, "reasoning_content", None)
                if reasoning_chunk is not None:
                    if not first_reasoning_emitted:
                        # Prepend the opening tag for the first reasoning chunk.
                        yield ChunkResponse(
                            content=f"<llm_reasoning_token>{reasoning_chunk}",
                            is_complete=False
                        )
                        first_reasoning_emitted = True
                    else:
                        yield ChunkResponse(
                            content=reasoning_chunk,
                            is_complete=False
                        )
                    # Accumulate the raw reasoning token (without the prepended tag)
                    reasoning_content += reasoning_chunk

                # Process main content tokens.
                main_token = chunk.choices[0].delta.content
                if main_token is not None:
                    if first_reasoning_emitted and not reasoning_closed:
                        # Before yielding the first main content token, close the reasoning section.
                        yield ChunkResponse(
                            content="</llm_reasoning_token>\n",
                            is_complete=False
                        )
                        reasoning_closed = True
                    accumulated_content += main_token
                    yield ChunkResponse(
                        content=main_token,
                        is_complete=False
                    )

                # Yield token usage if available.
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    token_usage = self._create_token_usage(chunk.usage)
                    yield ChunkResponse(
                        content="",
                        is_complete=True,
                        usage=token_usage
                    )

            # End of stream: if only reasoning tokens were received and the closing tag has not been yielded,
            # yield it now.
            if first_reasoning_emitted and not reasoning_closed:
                yield ChunkResponse(
                    content="</llm_reasoning_token>\n",
                    is_complete=False
                )
            
            # After streaming, add the assistant message with or without reasoning content.
            if reasoning_content:
                self.add_assistant_message(accumulated_content, reasoning_content=reasoning_content)
            else:
                self.add_assistant_message(accumulated_content)
            logger.info("Completed streaming response from DeepSeek API")
        except Exception as e:
            logger.error(f"Error in DeepSeek API streaming: {str(e)}")
            raise ValueError(f"Error in DeepSeek API streaming: {str(e)}")
    
    async def cleanup(self):
        await super().cleanup()
