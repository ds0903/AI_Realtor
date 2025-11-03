"""
FastAPI для аналітики ШІ Ріелтора
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from database import get_session, Conversation
import config

app = FastAPI(title="AI Realtor API", version="1.0.0")

@app.get("/")
async def root():
    """Головна сторінка API"""
    return {
        "message": "AI Realtor API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/conversations")
async def get_conversations(
    skip: int = 0,
    limit: int = 10,
    session: AsyncSession = Depends(get_session)
):
    """Отримати список всіх розмов"""
    result = await session.execute(
        select(Conversation).offset(skip).limit(limit)
    )
    conversations = result.scalars().all()
    return {"conversations": [
        {
            "id": c.id,
            "user_id": c.user_id,
            "username": c.username,
            "phone_number": c.phone_number,
            "filters": c.filters,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        }
        for c in conversations
    ]}

@app.get("/conversations/{user_id}")
async def get_conversation(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Отримати конкретну розмову за user_id"""
    result = await session.execute(
        select(Conversation).where(Conversation.user_id == user_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "username": conversation.username,
        "phone_number": conversation.phone_number,
        "messages": conversation.messages,
        "filters": conversation.filters,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
    }

@app.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Отримати статистику"""
    result = await session.execute(select(Conversation))
    conversations = result.scalars().all()
    
    total = len(conversations)
    with_phone = len([c for c in conversations if c.phone_number])
    
    return {
        "total_conversations": total,
        "conversations_with_phone": with_phone,
        "conversion_rate": round(with_phone / total * 100, 2) if total > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
