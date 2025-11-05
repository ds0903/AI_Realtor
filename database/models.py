"""
Моделі бази даних
"""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    """Модель для збереження розмов"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True, unique=True)
    username = Column(String(255))
    phone_number = Column(String(50))
    messages = Column(JSON)  # Залишаємо для сумісності
    filters = Column(JSON)
    offset = Column(Integer, default=0)  # Для пагінації варіантів
    total_found = Column(Integer, default=0)  # Скільки всього знайдено
    initial_total = Column(Integer, default=0)  # Початкова кількість результатів (не змінюється)
    last_query_params = Column(JSON)  # Останні параметри запиту
    last_shown_apartments = Column(JSON)  # Останні показані об'єкти
    last_activity = Column(DateTime)  # Час останньої активності (для очищення)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Зв'язок з повідомленнями
    message_history = relationship("MessageHistory", back_populates="conversation", cascade="all, delete-orphan")

class MessageHistory(Base):
    """Модель для збереження історії повідомлень"""
    __tablename__ = 'message_history'
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    user_message = Column(Text)  # Що написав користувач
    bot_response = Column(Text)  # Що відповів бот
    timestamp = Column(DateTime, default=datetime.now)
    
    # Зв'язок з розмовою
    conversation = relationship("Conversation", back_populates="message_history")
