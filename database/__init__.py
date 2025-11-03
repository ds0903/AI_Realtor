"""
Ініціалізація бази даних
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base, Conversation, MessageHistory
import config

# Створюємо асинхронний engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    future=True
)

# Створюємо фабрику сесій
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Ініціалізація бази даних - створення таблиць"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Експортуємо все що потрібно
__all__ = ['async_session', 'init_db', 'Conversation', 'MessageHistory']
