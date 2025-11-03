"""
Telegram бот для ШІ Ріелтора
"""
import asyncio
import logging
import json
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy import select
from datetime import datetime

import config
from database import async_session, Conversation, MessageHistory, init_db
from ai import claude_agent
from ai.prompts import get_success_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

async def save_message_pair(user_id, user_message, bot_response):
    """Зберігає пару повідомлень (користувач + бот) в БД"""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            # Створюємо новий запис в історії
            message_record = MessageHistory(
                conversation_id=conversation.id,
                user_message=user_message,
                bot_response=bot_response,
                timestamp=datetime.now()
            )
            session.add(message_record)
            
            # Оновлюємо updated_at в conversation
            conversation.updated_at = datetime.now()
            
            # Також зберігаємо в JSON для сумісності
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
            
            await session.commit()
            logger.info(f"💾 Збережено пару повідомлень для user {user_id}")
        else:
            logger.error(f"❌ Conversation не знайдено для user {user_id}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обробка команди /start"""
    user_id = message.from_user.id
    
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            conversation = Conversation(
                user_id=user_id,
                username=message.from_user.username,
                messages=[],
                filters={}
            )
            session.add(conversation)
            await session.commit()
            logger.info(f"✅ Створено нову conversation для user {user_id}")
    
    # Отримуємо привітання від AI
    response = await claude_agent.process_message(user_id, "/start")
    
    logger.info(f"🤖 AI Response: {response['response'][:100]}")
    
    # Зберігаємо пару повідомлень
    await save_message_pair(user_id, "/start", response["response"])
    
    # Оновлюємо фільтри
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.filters = response.get("filters", {})
            await session.commit()
    
    await message.answer(response["response"])

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    """Обробка контакту користувача"""
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            conversation.phone_number = phone_number
            conversation.updated_at = datetime.now()
            
            # Зберігаємо отримання контакту
            message_record = MessageHistory(
                conversation_id=conversation.id,
                user_message=f"[КОНТАКТ: {phone_number}]",
                bot_response="",
                timestamp=datetime.now()
            )
            session.add(message_record)
            
            await session.commit()
            
            # Формуємо запит до API
            filters = conversation.filters or {}
            
            # Формуємо параметри для API
            api_params = {
                "key": config.PROPERTY_API_KEY,
                "limit": 3,
                "offset": 0
            }
            
            # Додаємо фільтри
            if filters.get("price_min"):
                api_params["price_min"] = int(filters["price_min"])
            if filters.get("price_max"):
                api_params["price_max"] = int(filters["price_max"])
            if filters.get("rooms"):
                api_params["rooms_in"] = int(filters["rooms"])
            if filters.get("area_min"):
                api_params["area_min"] = int(filters["area_min"])
            if filters.get("area_max"):
                api_params["area_max"] = int(filters["area_max"])
            if filters.get("floor"):
                api_params["floor_min"] = int(filters["floor"])
            
            # Логуємо запит
            logger.info(f"📞 API REQUEST")
            logger.info(f"   User: {phone_number} (ID: {user_id})")
            logger.info(f"   Filters: {json.dumps(filters, ensure_ascii=False)}")
            logger.info(f"   Params: {json.dumps(api_params, ensure_ascii=False)}")
            
            try:
                async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                    api_response = await client.post(
                        config.PROPERTY_API_URL,
                        json=api_params
                    )
                    
                    logger.info(f"   Response: {api_response.status_code}")
                    
                    # Зберігаємо результат API
                    api_result_msg = MessageHistory(
                        conversation_id=conversation.id,
                        user_message="[API REQUEST]",
                        bot_response=f"Status: {api_response.status_code}, Body: {api_response.text[:500]}",
                        timestamp=datetime.now()
                    )
                    session.add(api_result_msg)
                    await session.commit()
                    
                    success_msg = get_success_message(api_success=(api_response.status_code == 200))
                    
                    # Зберігаємо фінальне повідомлення
                    final_msg = MessageHistory(
                        conversation_id=conversation.id,
                        user_message="",
                        bot_response=success_msg,
                        timestamp=datetime.now()
                    )
                    session.add(final_msg)
                    await session.commit()
                    
                    await message.answer(success_msg, reply_markup=ReplyKeyboardRemove())
                    
            except Exception as e:
                logger.error(f"❌ API error: {e}")
                error_msg = get_success_message(api_success=False)
                
                # Зберігаємо помилку
                error_record = MessageHistory(
                    conversation_id=conversation.id,
                    user_message="[API ERROR]",
                    bot_response=f"Error: {str(e)}",
                    timestamp=datetime.now()
                )
                session.add(error_record)
                await session.commit()
                
                await message.answer(error_msg, reply_markup=ReplyKeyboardRemove())

@dp.message(F.text)
async def handle_message(message: types.Message):
    """Обробка текстових повідомлень"""
    user_id = message.from_user.id
    user_message = message.text
    
    logger.info(f"👤 User {user_id}: {user_message}")
    
    # Перевіряємо чи існує конверсація
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            # Створюємо нову
            conversation = Conversation(
                user_id=user_id,
                username=message.from_user.username,
                messages=[],
                filters={}
            )
            session.add(conversation)
            await session.commit()
            logger.info(f"✅ Створено conversation для user {user_id}")
    
    # Отримуємо відповідь від AI
    response = await claude_agent.process_message(user_id, user_message)
    
    bot_response = response["response"]
    
    logger.info(f"🤖 Bot: {bot_response[:100]}...")
    logger.info(f"📊 Filters: {response.get('filters', {})}")
    logger.info(f"❓ Questions: {response.get('questions_asked', [])}")
    logger.info(f"✅ Ready: {response.get('ready_for_contact', False)}")
    
    # Зберігаємо пару повідомлень
    await save_message_pair(user_id, user_message, bot_response)
    
    # Оновлюємо фільтри
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            conversation.filters = response.get("filters", conversation.filters)
            conversation.updated_at = datetime.now()
            await session.commit()
    
    # Відправляємо відповідь
    if response.get("ready_for_contact"):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Поділитись контактом", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(bot_response, reply_markup=keyboard)
    else:
        await message.answer(bot_response)

async def main():
    """Головна функція запуску бота"""
    await init_db()
    logger.info("=" * 60)
    logger.info("✅ База даних ініціалізована")
    logger.info("🤖 Бот запускається...")
    logger.info("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
