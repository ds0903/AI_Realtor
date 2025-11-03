"""
Скрипт для очищення та перестворення БД
"""
import asyncio
from database import init_db, engine
from database.models import Base

async def reset_database():
    """Видаляє та перестворює всі таблиці"""
    print("=" * 60)
    print("🗑️  ОЧИЩЕННЯ БАЗИ ДАНИХ")
    print("=" * 60)
    
    try:
        # Видаляємо всі таблиці
        async with engine.begin() as conn:
            print("❌ Видалення старих таблиць...")
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ Таблиці видалено")
        
        # Створюємо нові таблиці
        async with engine.begin() as conn:
            print("📝 Створення нових таблиць...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Таблиці створено")
        
        print("\n" + "=" * 60)
        print("✅ БАЗА ДАНИХ ОНОВЛЕНА!")
        print("=" * 60)
        print("\nСтруктура:")
        print("  📋 conversations - головна таблиця")
        print("  💬 message_history - історія повідомлень")
        print("\nТепер можна запускати бота:")
        print("  python run_bot.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("\n⚠️  УВАГА! Це видалить ВСІ дані з БД!")
    answer = input("Продовжити? (yes/no): ")
    
    if answer.lower() in ['yes', 'y', 'так', 'т']:
        asyncio.run(reset_database())
    else:
        print("❌ Скасовано")
