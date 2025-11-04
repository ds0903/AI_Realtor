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
import re

def get_manager_availability():
    """Повертає інформацію про доступність менеджера"""
    now = datetime.now()
    weekday = now.weekday()  # 0 = понеділок, 6 = неділя
    current_hour = now.hour
    
    weekday_names = [
        'понеділок', 'вівторок', 'середу', 'четвер', 
        "п'ятницю", 'суботу', 'неділю'
    ]
    
    # Перевіряємо чи зараз робочий час (пн-пт 10-18)
    if weekday < 5 and 10 <= current_hour < 18:
        return "Менеджер зв'яжеться з вами найближчим часом (сьогодні до 18:00)."
    
    # Якщо сьогодні робочий день, але після 18:00
    if weekday < 5 and current_hour >= 18:
        if weekday == 4:  # п'ятниця
            return "Менеджер зв'яжеться з вами в понеділок з 10:00 до 18:00."
        else:
            next_day = weekday_names[weekday + 1]
            return f"Менеджер зв'яжеться з вами в {next_day} з 10:00 до 18:00."
    
    # Якщо сьогодні робочий день, але до 10:00
    if weekday < 5 and current_hour < 10:
        today = weekday_names[weekday]
        return f"Менеджер зв'яжеться з вами сьогодні ({today}) з 10:00 до 18:00."
    
    # Якщо субота
    if weekday == 5:
        return "Менеджер зв'яжеться з вами в понеділок з 10:00 до 18:00."
    
    # Якщо неділя
    if weekday == 6:
        return "Менеджер зв'яжеться з вами в понеділок з 10:00 до 18:00."
    
    return "Менеджер зв'яжеться з вами у робочий час (пн-пт з 10:00 до 18:00)."

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
                    
                    # Якщо користувач мовчить 60+ секунд і ми ще не відправляли silence
                    if time_diff >= 60 and not silence_sent.get(user_id, False):
                        # Перевіряємо чи користувач в процесі розмови (не отримав контакт)
                        async with async_session() as session:
                            result = await session.execute(
                                select(Conversation).where(Conversation.user_id == user_id)
                            )
                            conversation = result.scalar_one_or_none()
                            
                            # Відправляємо silence тільки якщо:
                            # 1. Є розмова
                            # 2. Немає контакту
                            # 3. Є хоча б одне питання на яке відповів користувач
                            if conversation and not conversation.phone_number:
                                # Перевіряємо чи є хоча б одне повідомлення (окрім /start)
                                result_history = await session.execute(
                                    select(MessageHistory)
                                    .where(MessageHistory.conversation_id == conversation.id)
                                    .where(MessageHistory.user_message != "/start")
                                    .where(MessageHistory.user_message != "[SILENCE TRIGGER]")
                                    .where(MessageHistory.user_message != "[API REQUEST]")
                                    .where(MessageHistory.user_message != "[API ERROR]")
                                )
                                has_messages = result_history.scalar_one_or_none() is not None
                                
                                if has_messages:
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

async def fetch_and_send_apartments(message: types.Message, user_id: int, offset_increment: bool = False):
    """
    Отримує і відправляє варіанти квартир
    
    Args:
        message: повідомлення користувача
        user_id: ID користувача
        offset_increment: чи збільшувати offset (для show_more)
    """
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return
        
        filters = conversation.filters or {}
        phone_number = conversation.phone_number
        
        # Ініціалізуємо offset якщо None (для старих записів)
        if conversation.offset is None:
            conversation.offset = 0
            await session.commit()
        
        # Формуємо параметри для API
        api_params = {
            "key": config.PROPERTY_API_KEY,
            "limit": 3,
            "offset": (conversation.offset + 3) if offset_increment else conversation.offset
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
            "Нефтяніків": 109,
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
            if district_name.lower() not in ["всі райони", "всі", "будь-який", "неважливо"]:
                if district_name in microarea_mapping:
                    api_params["microarea_id"] = microarea_mapping[district_name]
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
        
        # Зберігаємо параметри запиту
        conversation.last_query_params = api_params
        await session.commit()
        
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
                    
                    # Перевіряємо що items не None
                    if items is None:
                        items = []
                    
                    # Оновлюємо offset
                    if offset_increment:
                        conversation.offset += len(items)
                    else:
                        conversation.offset = len(items)
                    
                    # Підраховуємо загальну кількість
                    # Робимо запит з великим offset щоб знайти всі
                    all_items = list(items)  # Зберігаємо поточні
                    current_offset = api_params.get('offset', 0) + len(items)
                    
                    # Продовжуємо запити поки є результати
                    while True:
                        count_params = api_params.copy()
                        count_params['offset'] = current_offset
                        count_params['limit'] = 100
                        
                        try:
                            count_response = await client.post(config.PROPERTY_API_URL, json=count_params)
                            if count_response.status_code == 200:
                                count_data = count_response.json()
                                count_items = count_data.get('items', [])
                                if count_items:
                                    all_items.extend(count_items)
                                    current_offset += len(count_items)
                                    if len(count_items) < 100:
                                        break
                                else:
                                    break
                            else:
                                break
                        except:
                            break
                    
                    total_found = len(all_items)
                    
                    await session.commit()
                    
                    logger.info(f"🏠 Found {len(items)} apartments, total: {total_found}, offset: {conversation.offset}")
                    
                    # Зберігаємо результат API
                    api_result_msg = MessageHistory(
                        conversation_id=conversation.id,
                        user_message="[API REQUEST]",
                        bot_response=f"Status: 200, Items: {len(items)}, Total: {total_found}, Offset: {conversation.offset}",
                        timestamp=datetime.now()
                    )
                    session.add(api_result_msg)
                    await session.commit()
                    
                    if items:
                        # Зберігаємо показані об'єкти
                        conversation.last_shown_apartments = items
                        await session.commit()
                        
                        # Відправляємо повідомлення про початок
                        await message.answer(
                            f"🏠 Відмінно! Я підібрав {len(items)} варіанти для вас:\n\n",
                            reply_markup=ReplyKeyboardRemove()
                        )
                        
                        # Відправляємо кожен варіант
                        start_idx = conversation.offset - len(items) + 1
                        for idx, apt in enumerate(items, start_idx):
                            await send_apartment(message, apt, idx)
                        
                        # Перевіряємо чи є ще варіанти (робимо тестовий запит)
                        test_params = api_params.copy()
                        test_params['offset'] = conversation.offset
                        test_params['limit'] = 1
                        
                        test_response = await client.post(config.PROPERTY_API_URL, json=test_params)
                        has_more = False
                        if test_response.status_code == 200:
                            test_data = test_response.json()
                            test_items = test_data.get('items', [])
                            has_more = len(test_items) > 0
                        
                        # Повідомлення в кінці
                        if has_more:
                            final_message = f"📊 Показано {conversation.offset} з {total_found} варіантів.\n\n"
                            final_message += "Напишіть 'Покажіть ще варіанти' щоб побачити більше."
                        else:
                            final_message = f"📊 Показано всі {total_found} варіантів."
                        
                        await message.answer(final_message, parse_mode="HTML")
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
    
    # Використовуємо нову функцію для відправки варіантів
    await fetch_and_send_apartments(message, user_id)

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
    action = response.get("action")
    
    logger.info(f"🤖 Bot: {bot_response[:100]}...")
    logger.info(f"📊 Filters: {response.get('filters', {})}")
    logger.info(f"❓ Questions: {response.get('questions_asked', [])}")
    logger.info(f"✅ Ready: {response.get('ready_for_contact', False)}")
    logger.info(f"🎬 Action: {action}")
    
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
    
    # Перевіряємо чи це запит на show_more (якщо AI не розпізнав)
    if not action:
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            
            if conversation and conversation.last_shown_apartments:
                show_more_keywords = [
                    'ще варіант', 'ще квартир', 'покажи ще', 'покажіть ще',
                    'показати ще', 'більше варіант', 'більше квартир',
                    'наступн', 'далі', 'інші варіант'
                ]
                if any(keyword in user_message.lower() for keyword in show_more_keywords):
                    action = "show_more"
    
    # Обробляємо дії користувача
    if action == "show_more":
        # Показати ще варіанти
        await message.answer("Зачекайте, шукаю ще варіанти...")
        await fetch_and_send_apartments(message, user_id, offset_increment=True)
        return
    
    elif action == "schedule_viewing":
        # Запис на перегляд
        
        # Зберігаємо запис в Google Sheets
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Conversation).where(Conversation.user_id == user_id)
                )
                conversation = result.scalar_one_or_none()
                
                if conversation:
                    user_data = {
                        'name': conversation.filters.get('name', 'Не вказано'),
                        'phone': conversation.phone_number or 'Не вказано',
                        'username': f"@{message.from_user.username}" if message.from_user.username else 'Не вказано',
                        'filters': conversation.filters
                    }
                    
                    # Дані про обраний об'єкт (беремо перший з останніх показаних)
                    apartment_data = None
                    if conversation.last_shown_apartments and len(conversation.last_shown_apartments) > 0:
                        apt = conversation.last_shown_apartments[0]
                        
                        # Витягуємо адресу
                        address_obj = apt.get('address', {})
                        if isinstance(address_obj, dict):
                            street = address_obj.get('street', '')
                            house = address_obj.get('house_number', '')
                        else:
                            street = ''
                            house = ''
                        
                        # Витягуємо ціну
                        prices_obj = apt.get('prices', {})
                        if isinstance(prices_obj, dict):
                            price = prices_obj.get('value', '')
                        else:
                            price = ''
                        
                        apartment_data = {
                            'id': apt.get('id', ''),
                            'street': street,
                            'house': house,
                            'rooms': apt.get('rooms', ''),
                            'area': apt.get('area_total', ''),
                            'floor': apt.get('floor', ''),
                            'price': price
                        }
                    
                    sheets_service.add_viewing_request(user_data, apartment_data)
                    logger.info(f"✅ Записано на перегляд user {user_id}")
            
            # Відповідь користувачу з інформацією про робочий час
            manager_info = get_manager_availability()
            if bot_response and bot_response.strip():
                await message.answer(f"{bot_response}\n\n{manager_info}")
            else:
                await message.answer(
                    f"Відмінно! Записую вас на перегляд. {manager_info}"
                )
        except Exception as e:
            logger.error(f"❌ Помилка при записі на перегляд: {e}")
            manager_info = get_manager_availability()
            await message.answer(
                f"Дякую! Ваша заявка прийнята. {manager_info}"
            )
        return
    
    elif action == "change_filters":
        # Зміна параметрів - скидаємо offset
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            
            if conversation:
                conversation.offset = 0
                await session.commit()
        
        if bot_response and bot_response.strip():
            await message.answer(bot_response)
        
        # Перевіряємо чи є контакт, якщо є - відправляємо нові варіанти
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            
            if conversation and conversation.phone_number:
                await fetch_and_send_apartments(message, user_id)
        return
    
    # Відправляємо відповідь
    if response.get("ready_for_contact"):
        # Перевіряємо чи вже є контакт
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result.scalar_one_or_none()
            
            if conversation and conversation.phone_number:
                # Перевіряємо чи це запит на перегляд / консультацію
                viewing_keywords = [
                    'запис', 'перегляд', 'оглян', 'подивит', 'запиш', 'viewing', 
                    'огляду', 'записати', 'записую', 'сподобав', 'подобає', 
                    'консультац', 'поспілкуват', 'поспілкувати', 
                    'рієлтор', 'менеджер', "зв'язати", 'цікавить', 'цікавлять'
                ]
                is_viewing_request = any(keyword in user_message.lower() for keyword in viewing_keywords)
                
                if is_viewing_request and conversation.last_shown_apartments:
                    # Це запит на перегляд - визначаємо які варіанти
                    try:
                        # Шукаємо номери варіантів у повідомленні
                        variant_numbers = re.findall(r'(\d+)', user_message)
                        
                        apartments_to_save = []
                        
                        if variant_numbers:
                            # Якщо вказані конкретні номери
                            # Визначаємо початковий індекс для показаних варіантів
                            start_offset = conversation.offset - len(conversation.last_shown_apartments)
                            
                            for num_str in variant_numbers:
                                variant_num = int(num_str)
                                # Обчислюємо індекс в масиві last_shown_apartments
                                array_idx = variant_num - start_offset - 1
                                
                                if 0 <= array_idx < len(conversation.last_shown_apartments):
                                    apt = conversation.last_shown_apartments[array_idx]
                                    # Перевіряємо що цей варіант ще не додано
                                    apt_id = apt.get('id')
                                    if not any(a.get('id') == apt_id for a in apartments_to_save):
                                        apartments_to_save.append(apt)
                        else:
                            # Якщо номери не вказані - беремо всі показані
                            apartments_to_save = conversation.last_shown_apartments
                        
                        # Зберігаємо кожен варіант
                        user_data = {
                            'name': conversation.filters.get('name', 'Не вказано'),
                            'phone': conversation.phone_number or 'Не вказано',
                            'username': f"@{message.from_user.username}" if message.from_user.username else 'Не вказано',
                            'filters': conversation.filters
                        }
                        
                        for apt in apartments_to_save:
                            # Витягуємо адресу
                            address_obj = apt.get('address', {})
                            if isinstance(address_obj, dict):
                                street = address_obj.get('street', '')
                                house = address_obj.get('house_number', '')
                            else:
                                street = ''
                                house = ''
                            
                            # Витягуємо ціну
                            prices_obj = apt.get('prices', {})
                            if isinstance(prices_obj, dict):
                                price = prices_obj.get('value', '')
                            else:
                                price = ''
                            
                            apartment_data = {
                                'id': apt.get('id', ''),
                                'street': street,
                                'house': house,
                                'rooms': apt.get('rooms', ''),
                                'area': apt.get('area_total', ''),
                                'floor': apt.get('floor', ''),
                                'price': price
                            }
                            
                            sheets_service.add_viewing_request(user_data, apartment_data)
                        
                        logger.info(f"✅ Записано на перегляд {len(apartments_to_save)} варіант(ів) для user {user_id}")
                        
                        manager_info = get_manager_availability()
                        if len(apartments_to_save) > 1:
                            await message.answer(
                                f"Дякую! Записую вас на перегляд {len(apartments_to_save)} варіантів. {manager_info}"
                            )
                        else:
                            await message.answer(
                                f"Дякую! Записую вас на перегляд варіанта. {manager_info}"
                            )
                    except Exception as e:
                        logger.error(f"❌ Помилка при записі на перегляд: {e}")
                        manager_info = get_manager_availability()
                        await message.answer(
                            f"Дякую! Ваша заявка прийнята. {manager_info}"
                        )
                elif not conversation.last_shown_apartments:
                    # Ще не показували варіанти - показуємо вперше
                    await fetch_and_send_apartments(message, user_id)
                else:
                    # Вже показували варіанти - просто відповідаємо
                    if bot_response and bot_response.strip():
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
                if bot_response and bot_response.strip():  # Перевіряємо що відповідь не порожня
                    await message.answer(bot_response, reply_markup=keyboard)
    else:
        # Відправляємо звичайну відповідь тільки якщо вона не порожня
        if bot_response and bot_response.strip():
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
