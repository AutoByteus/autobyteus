from typing import Optional, List, Tuple, AsyncGenerator
from autobyteus.llm.base_llm import BaseLLM

class Conversation:
    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.conversation_history: List[Tuple[str, str]] = []

    async def send_user_message(self, user_input: str, file_paths: Optional[List[str]] = None) -> str:
        user_message_index = len([entry for entry in self.conversation_history if entry[0] == "user"])
        response = await self.llm.send_user_message(user_input, file_paths, user_message_index=user_message_index)
        
        # Combine user input and file paths into a single message for the conversation history
        combined_user_message = user_input
        if file_paths:
            combined_user_message += f"\n[Files sent: {', '.join(file_paths)}]"
        # Add the combined user message to the conversation history
        self.conversation_history.append(("user", combined_user_message))
        self.conversation_history.append(("assistant", response))
        return response

    async def stream_user_message(self, user_input: str, file_paths: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        """
        Stream a user message and get response tokens incrementally.
        
        Args:
            user_input: The user's message
            file_paths: Optional list of file paths to include in context
            
        Yields:
            Response tokens as they become available
        """
        user_message_index = len([entry for entry in self.conversation_history if entry[0] == "user"])
        
        # Combine user input and file paths into a single message for the conversation history
        combined_user_message = user_input
        if file_paths:
            combined_user_message += f"\n[Files sent: {', '.join(file_paths)}]"
        
        # Add the user message to history before streaming starts
        self.conversation_history.append(("user", combined_user_message))
        
        complete_response = ""
        async for token in self.llm.stream_user_message(user_input, file_paths, user_message_index=user_message_index):
            complete_response += token
            yield token
        
        # After streaming is complete, add the full response to conversation history
        self.conversation_history.append(("assistant", complete_response))

    def get_conversation_history(self, page: int = 1, page_size: int = 10) -> List[Tuple[str, str]]:
        start = (page - 1) * page_size
        end = start + page_size
        return self.conversation_history[start:end]