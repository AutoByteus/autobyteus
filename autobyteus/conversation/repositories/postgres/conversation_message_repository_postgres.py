# File: autobyteus/autobyteus/conversation/repositories/postgres/conversation_message_repository_postgres.py

from sqlalchemy import Column, Integer, String, DateTime
from repository_sqlalchemy import Base, BaseRepository, transaction
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    @transaction()
    def create_message(self, conversation_name: str, role: str, message: str) -> ConversationMessage:
        """
        Create a new conversation message.

        Args:
            conversation_name (str): The name of the conversation.
            role (str): The role of the message sender.
            message (str): The content of the message.

        Returns:
            ConversationMessage: The created message object.
        """
        try:
            new_message = ConversationMessage(
                conversation_name=conversation_name,
                role=role,
                message=message
            )
            return self.create(new_message)
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise

    @transaction()
    def get_messages_by_conversation(self, conversation_name: str):
        """
        Retrieve all messages for a given conversation.

        Args:
            conversation_name (str): The name of the conversation.

        Returns:
            List[ConversationMessage]: A list of conversation messages.
        """
        try:
            return self.session.query(self.model).filter_by(conversation_name=conversation_name).all()
        except Exception as e:
            logger.error(f"Error retrieving messages: {str(e)}")
            raise

    @transaction()
    def update_message(self, message_id: int, new_content: str) -> ConversationMessage:
        """
        Update the content of an existing message.

        Args:
            message_id (int): The ID of the message to update.
            new_content (str): The new content for the message.

        Returns:
            ConversationMessage: The updated message object.
        """
        try:
            message = self.session.query(self.model).filter_by(id=message_id).first()
            if message:
                message.message = new_content
                return self.update(message)
            else:
                logger.warning(f"Message with id {message_id} not found")
                return None
        except Exception as e:
            logger.error(f"Error updating message: {str(e)}")
            raise

    @transaction()
    def delete_message(self, message_id: int) -> bool:
        """
        Delete a message by its ID.

        Args:
            message_id (int): The ID of the message to delete.

        Returns:
            bool: True if the message was deleted, False otherwise.
        """
        try:
            message = self.session.query(self.model).filter_by(id=message_id).first()
            if message:
                self.delete(message)
                return True
            else:
                logger.warning(f"Message with id {message_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            raise