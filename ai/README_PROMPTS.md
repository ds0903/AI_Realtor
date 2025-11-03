# 📝 Промпти для ШІ Ріелтора

## Структура файлу prompts.yml

Всі промпти зберігаються в окремому YML файлі: `ai/prompts.yml`

### Секції файлу:

#### 1. `system.main_prompt`
Головний системний промпт для Claude AI. Містить:
- Інструкції для AI
- Шаблони для привітань
- Список питань
- Заперечення та реакції
- Формат відповіді

**Змінні для підстановки:**
- `{welcome_messages}` - привітальні повідомлення з Google Sheets
- `{questions}` - 6 питань з Google Sheets
- `{objections}` - заперечення з Google Sheets
- `{reactions}` - реакції з Google Sheets

#### 2. `context.template`
Шаблон контексту для кожного повідомлення.

**Змінні для підстановки:**
- `{conversation_history}` - історія розмови (JSON)
- `{filters}` - зібрані фільтри (JSON)
- `{questions_asked}` - список заданих питань

#### 3. `contact_request.message`
Повідомлення з проханням поділитися контактом.

#### 4. `success_message`
Повідомлення після отримання контакту:
- `api_success` - коли API запит успішний
- `api_error` - коли є помилка API

## Як редагувати промпти

### 1. Відкрий файл
```bash
notepad ai/prompts.yml
```

### 2. Редагуй потрібну секцію
```yaml
system:
  main_prompt: |
    Твій новий текст промпта...
```

### 3. Збережи файл
Зміни застосуються автоматично при наступному запуску бота.

## Приклад використання в коді

```python
from ai.prompts import (
    get_system_prompt,
    get_context_prompt,
    get_contact_request_message,
    get_success_message
)

# Отримати системний промпт
system_prompt = get_system_prompt(
    welcome_messages=['Привіт!'],
    questions=['Як тебе звати?'],
    objections=['Розумію'],
    reactions=['Чудово!']
)

# Отримати контекст
context = get_context_prompt(
    conversation_history=[...],
    filters={...},
    questions_asked=[...]
)

# Отримати повідомлення запиту контакту
contact_msg = get_contact_request_message()

# Отримати повідомлення успіху
success_msg = get_success_message(api_success=True)
```

## Структура класу PromptsLoader

```python
class PromptsLoader:
    """Завантажувач промптів з YAML файлу"""
    
    def __init__(self, prompts_file='ai/prompts.yml'):
        # Завантажує промпти при ініціалізації
        
    def get_system_prompt(...):
        # Повертає системний промпт
        
    def get_context_prompt(...):
        # Повертає контекст промпт
        
    def get_contact_request_message():
        # Повертає повідомлення запиту контакту
        
    def get_success_message(api_success=True):
        # Повертає повідомлення успіху
```

## Переваги цього підходу

✅ **Легко редагувати** - всі тексти в одному місці  
✅ **Без перезапуску** - зміни застосуються автоматично  
✅ **Версійність** - легко відстежувати зміни в Git  
✅ **Багатомовність** - легко додати інші мови  
✅ **Чистий код** - промпти не засмічують Python код  

## Поради з редагування

1. **Використовуй YAML синтаксис**
   ```yaml
   # Для багаторядкових текстів
   key: |
     Перший рядок
     Другий рядок
   ```

2. **Зберігай форматування**
   - Пробіли важливі в YAML
   - Використовуй 2 пробіли для відступів

3. **Тестуй зміни**
   - Після змін перевір чи працює бот
   - Якщо є помилки - перевір синтаксис YAML

4. **Бекап**
   - Зроби копію перед великими змінами
   - Використовуй Git для версійності

## Розширення

Можна додати нові секції:

```yaml
# Додаткові повідомлення
additional_messages:
  error: "Вибачте, сталася помилка"
  timeout: "Час очікування вичерпано"
  
# Для різних мов
languages:
  uk:
    greeting: "Привіт!"
  en:
    greeting: "Hello!"
```

І використовувати в коді:

```python
prompts_loader.prompts['additional_messages']['error']
```
