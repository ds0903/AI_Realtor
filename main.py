"""
Головний файл запуску ШІ Ріелтора
"""
import asyncio
import uvicorn
from bot import main as bot_main

async def run_bot():
    """Запуск Telegram бота"""
    await bot_main()

def run_api():
    """Запуск FastAPI сервера"""
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ШІ Ріелтор - Запуск системи")
    print("=" * 50)
    print("\nВибери режим роботи:")
    print("1 - Тільки Telegram бот")
    print("2 - Тільки FastAPI сервер")
    print("3 - Обидва сервіси (в окремих процесах)")
    print("=" * 50)
    
    choice = input("\nТвій вибір (1/2/3): ").strip()
    
    if choice == "1":
        print("\n🚀 Запуск Telegram бота...\n")
        asyncio.run(bot_main())
    elif choice == "2":
        print("\n🚀 Запуск FastAPI сервера...\n")
        run_api()
    elif choice == "3":
        import multiprocessing
        
        print("\n🚀 Запуск обох сервісів...\n")
        
        # Процес для бота
        bot_process = multiprocessing.Process(
            target=lambda: asyncio.run(bot_main()),
            name="TelegramBot"
        )
        # Процес для API
        api_process = multiprocessing.Process(
            target=run_api,
            name="FastAPI"
        )
        
        bot_process.start()
        api_process.start()
        
        print("✅ Telegram бот запущено")
        print("✅ FastAPI сервер запущено на http://localhost:8000")
        print("\nНатисни Ctrl+C для зупинки\n")
        
        try:
            bot_process.join()
            api_process.join()
        except KeyboardInterrupt:
            print("\n\n👋 Зупинка сервісів...")
            bot_process.terminate()
            api_process.terminate()
            bot_process.join()
            api_process.join()
            print("✅ Всі сервіси зупинено")
    else:
        print("\n❌ Невірний вибір! Використовуй 1, 2 або 3")
