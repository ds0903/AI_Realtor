"""
Універсальний обробник повідомлень для всіх месенджерів
"""
import logging
from datetime import datetime
from sqlalchemy import select

from database import async_session, Conversation, MessageHistory
from ai import claude_agent

logger = logging.getLogger(__name__)

class MessageHandler:
    """Універсальна логіка обробки повідомлень"""
    
    @staticmethod
    async def save_message_pair(user_id: int, user_message: str, bot_response: str):
        """Зберігає пару повідомлень в БД"""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()

            if conversation:
                message_record = MessageHistory(
                    conversation_id=conversation.id,
                    user_message=user_message,
                    bot_response=bot_response,
                    timestamp=datetime.now()
                )
                session.add(message_record)
                conversation.updated_at = datetime.now()

                from sqlalchemy.orm.attributes import flag_modified
                messages = conversation.messages or []
                messages.append({
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                })
                messages.append({
                    "role": "assistant",
                    "content": bot_response,
                    "timestamp": datetime.now().isoformat()
                })
                conversation.messages = messages
                flag_modified(conversation, "messages")
                await session.commit()
    
    @staticmethod
    async def get_or_create_conversation(user_id: int, username: str = None):
        """Отримує або створює конверсацію"""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                conversation = Conversation(
                    user_id=user_id,
                    username=username,
                    messages=[],
                    filters={}
                )
                session.add(conversation)
                await session.commit()
                logger.info(f"✅ Створено conversation для user {user_id}")
                
        return conversation
    
    @staticmethod
    async def process_start_command(user_id: int, username: str = None):
        """Обробка команди /start"""
        await MessageHandler.get_or_create_conversation(user_id, username)
        
        response = await claude_agent.process_message(user_id, "/start")
        
        await MessageHandler.save_message_pair(user_id, "/start", response["response"])
        
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.filters = response.get("filters", {})
                await session.commit()
        
        return response
    
    @staticmethod
    async def process_text_message(user_id: int, text: str, username: str = None):
        """Обробка текстового повідомлення"""
        await MessageHandler.get_or_create_conversation(user_id, username)
        
        response = await claude_agent.process_message(user_id, text)
        
        await MessageHandler.save_message_pair(user_id, text, response["response"])
        
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.filters = response.get("filters", conversation.filters)
                conversation.updated_at = datetime.now()
                if conversation.last_shown_apartments:
                    conversation.last_activity = datetime.now()
                await session.commit()
        
        return response
    
    @staticmethod
    async def save_phone_number(user_id: int, phone: str):
        """Зберігає номер телефону"""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()

            if conversation:
                conversation.phone_number = phone
                conversation.updated_at = datetime.now()

                message_record = MessageHistory(
                    conversation_id=conversation.id,
                    user_message=f"[КОНТАКТ: {phone}]",
                    bot_response="",
                    timestamp=datetime.now()
                )
                session.add(message_record)
                await session.commit()
