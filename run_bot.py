"""
Швидкий запуск тільки Telegram бота
"""
import asyncio
import sys
from bot import main

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Запуск ШІ Ріелтор Telegram Bot")
    print("=" * 50)
    print("\nБот запускається...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Бот зупинено користувачем")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Помилка запуску: {e}")
        sys.exit(1)
