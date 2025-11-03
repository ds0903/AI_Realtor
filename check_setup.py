"""
Скрипт для перевірки налаштувань проекту
"""
import os
import sys

def check_env():
    """Перевірка .env файлу"""
    print("🔍 Перевірка .env файлу...")
    
    if not os.path.exists('.env'):
        print("❌ Файл .env не знайдено!")
        print("   Створи файл .env на основі .env.example")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required = [
        'TELEGRAM_BOT_TOKEN',
        'ANTHROPIC_API_KEY',
        'DB_PASSWORD',
        'PROPERTY_API_URL'
    ]
    
    missing = []
    for key in required:
        if not os.getenv(key):
            missing.append(key)
    
    if missing:
        print(f"❌ Відсутні змінні: {', '.join(missing)}")
        return False
    
    print("✅ Файл .env налаштовано")
    return True

def check_credentials():
    """Перевірка Google credentials"""
    print("\n🔍 Перевірка Google Sheets credentials...")
    
    if not os.path.exists('credentials.json'):
        print("❌ Файл credentials.json не знайдено!")
        print("   Дивись інструкцію в GOOGLE_SHEETS_SETUP.md")
        return False
    
    print("✅ Файл credentials.json знайдено")
    return True

def check_database():
    """Перевірка підключення до бази даних"""
    print("\n🔍 Перевірка підключення до PostgreSQL...")
    
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ai_realtor'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        conn.close()
        print("✅ Підключення до бази даних успішне")
        return True
    except Exception as e:
        print(f"❌ Помилка підключення до БД: {e}")
        print("   Перевір що PostgreSQL запущено і дані в .env правильні")
        return False

def check_sheets():
    """Перевірка Google Sheets"""
    print("\n🔍 Перевірка Google Sheets...")
    
    try:
        from services import sheets_service
        
        welcome = sheets_service.get_welcome_messages()
        questions = sheets_service.get_questions()
        
        if not welcome:
            print("⚠️  Аркуш 'Welcome' порожній")
        if not questions or len(questions) < 6:
            print("⚠️  Аркуш 'Questions' повинен містити 6 питань")
        
        if welcome and len(questions) >= 6:
            print("✅ Google Sheets налаштовано")
            print(f"   Знайдено {len(welcome)} привітань та {len(questions)} питань")
            return True
        return False
    except Exception as e:
        print(f"❌ Помилка доступу до Google Sheets: {e}")
        print("   Перевір права доступу для Service Account")
        return False

def check_structure():
    """Перевірка структури проекту"""
    print("\n🔍 Перевірка структури проекту...")
    
    required_dirs = ['bot', 'ai', 'database', 'services']
    required_files = ['config.py', 'main.py', 'api.py', 'requirements.txt']
    
    missing_dirs = [d for d in required_dirs if not os.path.isdir(d)]
    missing_files = [f for f in required_files if not os.path.isfile(f)]
    
    if missing_dirs:
        print(f"❌ Відсутні папки: {', '.join(missing_dirs)}")
        return False
    
    if missing_files:
        print(f"❌ Відсутні файли: {', '.join(missing_files)}")
        return False
    
    print("✅ Структура проекту коректна")
    return True

def main():
    """Головна функція перевірки"""
    print("=" * 60)
    print("🤖 Перевірка налаштувань ШІ Ріелтор")
    print("=" * 60)
    
    checks = [
        check_structure(),
        check_env(),
        check_credentials(),
        check_database(),
        check_sheets()
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ Всі перевірки пройдено успішно!")
        print("   Можеш запускати бота: python run_bot.py")
        print("   Або: python main.py")
    else:
        print("❌ Є проблеми з налаштуваннями")
        print("   Виправ помилки та запусти перевірку знову")
    print("=" * 60)
    
    return all(checks)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
