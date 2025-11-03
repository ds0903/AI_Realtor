"""
Тестовий скрипт для перевірки Google Sheets
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def test_google_sheets():
    """Тестує підключення до Google Sheets"""
    
    print("=" * 60)
    print("🧪 Тест Google Sheets API")
    print("=" * 60)
    
    # Крок 1: Перевірка файлу credentials.json
    print("\n1️⃣ Перевірка credentials.json...")
    if not os.path.exists('credentials.json'):
        print("   ❌ Файл credentials.json не знайдено!")
        print("   📁 Помісти файл в корінь проекту")
        return False
    print("   ✅ Файл credentials.json знайдено")
    
    # Крок 2: Читання email з credentials
    print("\n2️⃣ Читання Service Account email...")
    try:
        import json
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
            email = creds_data.get('client_email')
            project_id = creds_data.get('project_id')
            print(f"   📧 Email: {email}")
            print(f"   🔑 Project ID: {project_id}")
    except Exception as e:
        print(f"   ❌ Помилка читання файлу: {e}")
        return False
    
    # Крок 3: Перевірка .env
    print("\n3️⃣ Перевірка .env файлу...")
    from dotenv import load_dotenv
    load_dotenv()
    
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    if not sheet_id:
        print("   ❌ GOOGLE_SHEET_ID не знайдено в .env")
        print("   💡 Додай: GOOGLE_SHEET_ID=твій_id_таблиці")
        return False
    print(f"   ✅ Sheet ID: {sheet_id}")
    
    # Крок 4: Підключення до Google Sheets
    print("\n4️⃣ Спроба підключення до Google Sheets...")
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        print("   ✅ Авторизація успішна")
    except Exception as e:
        print(f"   ❌ Помилка авторизації: {e}")
        print("   💡 Можливо Google Sheets API не увімкнено")
        return False
    
    # Крок 5: Відкриття таблиці
    print("\n5️⃣ Спроба відкрити таблицю...")
    try:
        sheet = client.open_by_key(sheet_id)
        print(f"   ✅ Таблиця відкрита: {sheet.title}")
    except gspread.exceptions.SpreadsheetNotFound:
        print("   ❌ Таблиця не знайдена!")
        print(f"   📧 Переконайся що {email}")
        print("      має доступ до таблиці (Share → Editor)")
        return False
    except Exception as e:
        print(f"   ❌ Помилка: {e}")
        return False
    
    # Крок 6: Перевірка аркушів
    print("\n6️⃣ Перевірка аркушів...")
    required_sheets = ['Welcome', 'Questions', 'Objections', 'Reactions']
    worksheets = sheet.worksheets()
    worksheet_names = [ws.title for ws in worksheets]
    
    print(f"   📋 Знайдені аркуші: {', '.join(worksheet_names)}")
    
    missing = []
    for req_sheet in required_sheets:
        if req_sheet not in worksheet_names:
            missing.append(req_sheet)
    
    if missing:
        print(f"   ❌ Відсутні аркуші: {', '.join(missing)}")
        print("   💡 Створи ці аркуші в таблиці")
        return False
    print("   ✅ Всі необхідні аркуші присутні")
    
    # Крок 7: Перевірка даних
    print("\n7️⃣ Перевірка даних в аркушах...")
    
    # Welcome
    try:
        welcome_sheet = sheet.worksheet('Welcome')
        welcome_data = welcome_sheet.col_values(1)
        welcome_count = len([x for x in welcome_data if x.strip()])
        print(f"   ✅ Welcome: {welcome_count} повідомлень")
        if welcome_count == 0:
            print("      ⚠️  Аркуш порожній! Додай привітальні повідомлення")
    except Exception as e:
        print(f"   ❌ Welcome: {e}")
    
    # Questions
    try:
        questions_sheet = sheet.worksheet('Questions')
        questions_data = questions_sheet.col_values(1)
        questions_count = len([x for x in questions_data if x.strip()])
        print(f"   ✅ Questions: {questions_count} питань")
        if questions_count < 6:
            print("      ⚠️  Потрібно мінімум 6 питань!")
    except Exception as e:
        print(f"   ❌ Questions: {e}")
    
    # Objections
    try:
        objections_sheet = sheet.worksheet('Objections')
        objections_data = objections_sheet.col_values(1)
        objections_count = len([x for x in objections_data if x.strip()])
        print(f"   ✅ Objections: {objections_count} заперечень")
    except Exception as e:
        print(f"   ❌ Objections: {e}")
    
    # Reactions
    try:
        reactions_sheet = sheet.worksheet('Reactions')
        reactions_data = reactions_sheet.col_values(1)
        reactions_count = len([x for x in reactions_data if x.strip()])
        print(f"   ✅ Reactions: {reactions_count} реакцій")
    except Exception as e:
        print(f"   ❌ Reactions: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Тест пройдено успішно!")
    print("=" * 60)
    print(f"\n📧 Не забудь додати {email}")
    print("   в Share таблиці з правами Editor!")
    print("\n🚀 Можеш запускати бота: python run_bot.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        test_google_sheets()
    except Exception as e:
        print(f"\n❌ Критична помилка: {e}")
        print("\n📖 Читай інструкцію: GOOGLE_SHEETS_DETAILED.md")
