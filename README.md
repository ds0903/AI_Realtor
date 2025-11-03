# ШІ Ріелтор - Telegram Bot

Інтелектуальний чат-бот для підбору нерухомості з використанням Claude 4.5

## 📁 Структура проекту

```
AI_Realtor/
├── bot/                      # Telegram бот
│   ├── __init__.py
│   └── telegram_bot.py       # Основна логіка бота
├── ai/                       # AI агент
│   ├── __init__.py
│   ├── agent.py              # Claude агент
│   └── prompts.py            # Промпти для AI
├── database/                 # База даних
│   ├── __init__.py
│   └── models.py             # Моделі PostgreSQL
├── services/                 # Сервіси
│   ├── __init__.py
│   └── google_sheets.py      # Google Sheets інтеграція
├── config.py                 # Конфігурація
├── main.py                   # Головний запуск
├── run_bot.py                # Швидкий запуск бота
├── api.py                    # FastAPI для аналітики
├── check_setup.py            # Перевірка налаштувань
├── requirements.txt          # Залежності
├── .env                      # Змінні оточення (створи сам)
├── credentials.json          # Google credentials (створи сам)
├── README.md                 # Ця документація
├── QUICKSTART.md             # Швидкий старт
└── GOOGLE_SHEETS_SETUP.md    # Налаштування Google Sheets
```

## 🚀 Встановлення

### 1. Встанови залежності
```bash
pip install -r requirements.txt
```

### 2. Створи файл `.env`
```bash
copy .env.example .env
```

Заповни змінні:
- `TELEGRAM_BOT_TOKEN` - отримай у @BotFather
- `ANTHROPIC_API_KEY` - з https://console.anthropic.com/
- `DB_PASSWORD` - пароль від PostgreSQL
- `PROPERTY_API_URL` - URL для API запиту

### 3. Налаштуй Google Sheets
Дивись детальну інструкцію в `GOOGLE_SHEETS_SETUP.md`

### 4. Створи базу даних PostgreSQL
```sql
CREATE DATABASE ai_realtor;
```

### 5. Перевір налаштування
```bash
python check_setup.py
```

## ▶️ Запуск

### Швидкий запуск (тільки бот):
```bash
python run_bot.py
```

### Запуск з вибором режиму:
```bash
python main.py
```

Доступні режими:
- **1** - Тільки Telegram бот
- **2** - Тільки FastAPI сервер (http://localhost:8000)
- **3** - Обидва сервіси одночасно

### Окремий запуск API:
```bash
python api.py
```

## ✨ Функціонал

✅ **Природне спілкування** українською мовою  
✅ **6 питань** для збору інформації  
✅ **Адаптація** під стиль користувача  
✅ **Збір фільтрів** для підбору нерухомості  
✅ **Запит контакту** через Telegram кнопку  
✅ **POST запит** до API після отримання контакту  
✅ **Збереження історії** в PostgreSQL  
✅ **Тексти з Google Sheets** (легко редагувати)  
✅ **FastAPI** для аналітики та статистики  

## 🔧 API Endpoints

- `GET /` - статус API
- `GET /conversations` - список всіх розмов (з пагінацією)
- `GET /conversations/{user_id}` - конкретна розмова
- `GET /stats` - статистика (кількість розмов, конверсія)

Приклад запиту:
```bash
curl http://localhost:8000/conversations?skip=0&limit=10
```

## 📊 База даних

Модель `Conversation`:
- `id` - унікальний ідентифікатор
- `user_id` - Telegram ID користувача
- `username` - username користувача
- `phone_number` - номер телефону
- `messages` - історія повідомлень (JSON)
- `filters` - зібрані фільтри (JSON)
- `created_at` - дата створення
- `updated_at` - дата оновлення

## 🤖 AI Агент

Використовує **Claude Sonnet 4.5** для:
- Природного спілкування українською
- Розпізнавання намірів користувача
- Збору та структурування даних
- Адаптації під контекст розмови

Промпти знаходяться в `ai/prompts.py` і легко редагуються.

## 📝 Google Sheets

Тексти бота зберігаються в Google Sheets:
- **Welcome** - привітальні повідомлення
- **Questions** - 6 питань для збору даних
- **Objections** - відповіді на заперечення
- **Reactions** - реакції на відповіді
- **Districts** - список районів (опціонально)

Можна редагувати без зміни коду!

## 🔍 Перевірка налаштувань

Запусти перевірку перед стартом:
```bash
python check_setup.py
```

Скрипт перевірить:
- ✅ Структуру проекту
- ✅ Наявність .env файлу
- ✅ Google Sheets credentials
- ✅ Підключення до PostgreSQL
- ✅ Доступ до Google Sheets

## 📖 Додаткова документація

- `QUICKSTART.md` - швидкий старт за 5 хвилин
- `GOOGLE_SHEETS_SETUP.md` - детальна інструкція Google Sheets
- `.env.example` - приклад конфігурації

## 🛠️ Технології

- **aiogram 3.3** - Telegram Bot API
- **Claude Sonnet 4.5** - AI модель
- **FastAPI** - REST API
- **PostgreSQL** - база даних
- **SQLAlchemy** - ORM
- **Google Sheets API** - зберігання текстів

## 📞 Підтримка

Якщо виникли проблеми:
1. Запусти `python check_setup.py`
2. Перевір логи бота
3. Переконайся що всі сервіси запущені

## 📄 Ліцензія

Проект створено для тестового завдання.
