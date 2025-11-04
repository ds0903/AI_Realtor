"""
Telegram бот для ШІ Ріелтора
"""
import asyncio
import logging
import json
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
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

# Словник для зберігання часу останнього повідомлення користувача
user_last_message_time = {}
# Словник для відстеження чи вже відправлено silence повідомлення
silence_sent = {}

import random
from services.google_sheets import sheets_service

async def check_inactive_users():
    """Перевіряє неактивних користувачів і відправляє silence повідомлення"""
    while True:
        try:
            await asyncio.sleep(10)  # Перевіряємо кожні 10 секунд
            
            current_time = datetime.now()
            users_to_check = list(user_last_message_time.keys())
            
            for user_id in users_to_check:
                last_message_time = user_last_message_time.get(user_id)
                
                if last_message_time:
                    time_diff = (current_time - last_message_time).total_seconds()
                    
                    # Якщо користувач мовчить 30+ секунд і ми ще не відправляли silence
                    if time_diff >= 30 and not silence_sent.get(user_id, False):
                        # Перевіряємо чи користувач в процесі розмови (не отримав контакт)
                        async with async_session() as session:
                            result = await session.execute(
                                select(Conversation).where(Conversation.user_id == user_id)
                            )
                            conversation = result.scalar_one_or_none()
                            
                            # Відправляємо silence тільки якщо є розмова і немає контакту
                            if conversation and not conversation.phone_number:
                                silence_responses = sheets_service.get_silence_responses()
                                
                                if silence_responses:
                                    # Вибираємо випадкову відповідь
                                    silence_message = random.choice(silence_responses)
                                    
                                    try:
                                        await bot.send_message(user_id, silence_message)
                                        
                                        # Зберігаємо в базу
                                        await save_message_pair(user_id, "[SILENCE TRIGGER]", silence_message)
                                        
                                        # Позначаємо що відправили
                                        silence_sent[user_id] = True
                                        
                                        logger.info(f"🔕 Silence trigger for user {user_id}")
                                    except Exception as e:
                                        logger.error(f"❌ Error sending silence message to {user_id}: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Error in check_inactive_users: {e}")
            await asyncio.sleep(10)

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

async def send_apartment(message: types.Message, apartment: dict, index: int):
    """Відправляє інформацію про квартиру з усіма фото"""
    try:
        # Формуємо опис квартири
        title = apartment.get('title', 'Квартира')
        
        # Ціна з об'єкта prices
        prices_obj = apartment.get('prices', {})
        price = prices_obj.get('value', 0) if isinstance(prices_obj, dict) else 0
        
        rooms = apartment.get('rooms', 0)
        area = apartment.get('area_total', 0)
        floor = apartment.get('floor', '')
        floors_total = apartment.get('floors_total', '')
        
        # Адреса з об'єкта address
        address_obj = apartment.get('address', {})
        if isinstance(address_obj, dict):
            street_type = address_obj.get('street_type', '')
            street = address_obj.get('street', '')
            house = address_obj.get('house_number', '')
            address = f"{street_type} {street}, {house}" if street else ''
        else:
            address = ''
        
        description = apartment.get('description', '')
        
        # Форматуємо ціну
        price_formatted = f"{price:,.0f}".replace(',', ' ') if price else 'Ціна не вказана'
        
        caption = f"🏠 <b>Варіант #{index}</b>\n\n"
        caption += f"💰 <b>Ціна:</b> {price_formatted} $\n"
        caption += f"🚪 <b>Кімнат:</b> {rooms}\n"
        caption += f"📏 <b>Площа:</b> {area} м²\n"
        
        if floor and floors_total:
            caption += f"🏗️ <b>Поверх:</b> {floor}/{floors_total}\n"
        
        if address:
            caption += f"📍 <b>Адреса:</b> {address}\n"
        
        if description:
            # Обрізаємо опис до 200 символів
            desc_short = description[:200] + '...' if len(description) > 200 else description
            caption += f"\n📝 {desc_short}\n"
        
        # Парсимо фото з JSON string
        photos_raw = apartment.get('photos', [])
        photos = []
        
        if photos_raw and isinstance(photos_raw, list) and len(photos_raw) > 0:
            try:
                # photos приходить як список з одним JSON string
                photos_json = json.loads(photos_raw[0]) if isinstance(photos_raw[0], str) else photos_raw[0]
                
                # Формуємо URL фото
                base_url = 'https://re24.com.ua/'
                for photo in photos_json:
                    if isinstance(photo, dict):
                        # Беремо mini версію для швидшої загрузки
                        photo_path = photo.get('mini', photo.get('url', ''))
                        if photo_path:
                            photo_url = base_url + photo_path
                            photos.append(photo_url)
            except Exception as e:
                logger.error(f"❌ Error parsing photos: {e}")
        
        if photos:
            # Якщо є фото - відправляємо медіа-групу
            if len(photos) == 1:
                # Одне фото
                await message.answer_photo(
                    photo=photos[0],
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                # Кілька фото - медіа-група
                media_group = []
                for i, photo in enumerate(photos[:10]):  # Telegram максимум 10 фото
                    if i == 0:
                        # Перше фото з описом
                        media_group.append(InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"))
                    else:
                        media_group.append(InputMediaPhoto(media=photo))
                
                await message.answer_media_group(media=media_group)
        else:
            # Немає фото - просто текст
            await message.answer(caption, parse_mode="HTML")
        
        # Невелика затримка між варіантами
        await asyncio.sleep(0.5)
        
    except Exception as e:
        logger.error(f"❌ Error sending apartment: {e}")
        await message.answer(f"❌ Помилка при відправці варіанта #{index}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обробка команди /start"""
    user_id = message.from_user.id
    
    # Оновлюємо час останнього повідомлення
    user_last_message_time[user_id] = datetime.now()
    silence_sent[user_id] = False
    
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
    
    # Оновлюємо час і видаляємо з словників (розмова завершена)
    if user_id in user_last_message_time:
        del user_last_message_time[user_id]
    if user_id in silence_sent:
        del silence_sent[user_id]
    
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
            
            # Мапінг районів на ID
            district_mapping = {
                "Київський р-н": 5,
                "Малиновський р-н": 6,
                "Приморський р-н": 8,
                "Суворовський р-н": 11
            }
            
            # Мапінг мікрорайонів на ID
            microarea_mapping = {
                "Бугаївка": 89,
                "Дзержинського": 90,
                "Застава": 91,
                "Ленпоселок": 92,
                "Мельниця": 93,
                "Молдаванка": 94,
                "Сахарний": 95,
                "Слободка": 96,
                "Фонтан": 97,
                "Фонтанка": 97,
                "Черемушки": 98,
                "Аркадія": 99,
                "Центр": 102,
                "Пригород": 97,
                "Шевченко-Французький": 103,
                "Большевик": 104,
                "Котовського": 105,
                "Крива Балка": 106,
                "Куяльник": 107,
                "Лузановка": 108,
                "Нефтяників": 109,
                "Пересипь": 110,
                "Шевченко": 112,
                "Вузовський": 113,
                "Дача Ковалевського": 114,
                "Дружний": 115,
                "Таїрова": 116,
                "Царське село": 118,
                "Червоний хутор": 119,
                "Чорноморка": 121,
                "Чубаївка": 122
            }
            
            # Додаємо район/мікрорайон
            if filters.get("district"):
                district_name = filters["district"]
                # Перевіряємо чи не вказано "всі райони" чи подібне
                if district_name.lower() not in ["всі райони", "всі", "будь-який", "неважливо"]:
                    # Спочатку пробуємо знайти як мікрорайон
                    if district_name in microarea_mapping:
                        api_params["microarea_id"] = microarea_mapping[district_name]
                    # Потім як район
                    elif district_name in district_mapping:
                        api_params["district_id"] = district_mapping[district_name]
            
            # Додаємо кімнати
            if filters.get("rooms"):
                rooms_str = str(filters["rooms"])
                if rooms_str.isdigit():
                    api_params["rooms_in"] = int(rooms_str)
            
            # Додаємо стан (ремонт)
            if filters.get("state"):
                state = filters["state"].lower()
                if "ремонт" in state and "під" not in state:
                    api_params["condition_in"] = 7  # Жилая
                elif "під" in state:
                    api_params["condition_in"] = 6  # Під ремонт
            
            # Додаємо бюджет
            if filters.get("budget"):
                budget_str = str(filters["budget"])
                # Перевіряємо чи це число
                if budget_str.replace('.', '').replace(',', '').isdigit():
                    budget = int(float(budget_str.replace(',', '')))
                    api_params["price_max"] = budget
            elif filters.get("price_max"):
                price_max_str = str(filters["price_max"])
                if price_max_str.replace('.', '').replace(',', '').isdigit():
                    api_params["price_max"] = int(float(price_max_str.replace(',', '')))
            
            if filters.get("price_min"):
                price_min_str = str(filters["price_min"])
                if price_min_str.replace('.', '').replace(',', '').isdigit():
                    api_params["price_min"] = int(float(price_min_str.replace(',', '')))
            
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
                    
                    if api_response.status_code == 200:
                        data = api_response.json()
                        
                        logger.info(f"📊 API Response Data: {json.dumps(data, ensure_ascii=False)[:500]}")
                        
                        # Отримуємо дані
                        items = data.get('items', [])
                        total = len(items)  # API не повертає total, рахуємо самі
                        
                        logger.info(f"🏠 Found {len(items)} apartments, total: {total}")
                        
                        # Зберігаємо результат API
                        api_result_msg = MessageHistory(
                            conversation_id=conversation.id,
                            user_message="[API REQUEST]",
                            bot_response=f"Status: 200, Items: {len(items)}, Total: {total}",
                            timestamp=datetime.now()
                        )
                        session.add(api_result_msg)
                        await session.commit()
                        
                        if items:
                            # Відправляємо повідомлення про початок
                            await message.answer(
                                f"🏠 Відмінно! Я підібрав {len(items)} варіанти для вас:\n\n",
                                reply_markup=ReplyKeyboardRemove()
                            )
                            
                            # Відправляємо кожен варіант
                            for idx, apt in enumerate(items, 1):
                                await send_apartment(message, apt, idx)
                            
                            # В кінці повідомляємо скільки ще є
                            remaining = total - len(items)
                            if remaining > 0:
                                await message.answer(
                                    f"📊 Усього в базі знайдено <b>{total}</b> об'єктів за вашим запитом.\n"
                                    f"📁 Ще <b>{remaining}</b> варіантів доступно!\n\n"
                                    f"📞 Наш менеджер зв'яжеться з вами найближчим часом!",
                                    parse_mode="HTML"
                                )
                            else:
                                await message.answer(
                                    f"📞 Наш менеджер зв'яжеться з вами найближчим часом!"
                                )
                        else:
                            await message.answer(
                                "😔 На жаль, не знайдено варіантів за вашими параметрами.\n\n"
                                "📞 Наш менеджер зв'яжеться з вами для уточнення!",
                                reply_markup=ReplyKeyboardRemove()
                            )
                    else:
                        await message.answer(
                            "❗ Виникла помилка при пошуку. Наш менеджер зв'яжеться з вами.",
                            reply_markup=ReplyKeyboardRemove()
                        )
                    
            except Exception as e:
                logger.error(f"❌ API error: {e}")
                
                # Зберігаємо помилку
                error_record = MessageHistory(
                    conversation_id=conversation.id,
                    user_message="[API ERROR]",
                    bot_response=f"Error: {str(e)}",
                    timestamp=datetime.now()
                )
                session.add(error_record)
                await session.commit()
                
                await message.answer(
                    "❗ Виникла технічна помилка. Наш менеджер зв'яжеться з вами.",
                    reply_markup=ReplyKeyboardRemove()
                )

@dp.message(F.text)
async def handle_message(message: types.Message):
    """Обробка текстових повідомлень"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Оновлюємо час останнього повідомлення
    user_last_message_time[user_id] = datetime.now()
    # Скидаємо silence флаг
    silence_sent[user_id] = False
    
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
        # Перевіряємо чи вже є контакт
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            
            if conversation and conversation.phone_number:
                # Контакт вже є - просто відповідаємо
                await message.answer(bot_response)
            else:
                # Контакту немає - показуємо кнопку
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
    logger.info("🔔 Silence checker запускається...")
    logger.info("=" * 60)
    
    # Запускаємо фоновий таск для перевірки silence
    asyncio.create_task(check_inactive_users())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
