import os
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from groq import AsyncGroq

# Настройки Базы Данных 
DATABASE_URL = "sqlite+aiosqlite:///./drafts.db" 
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class DraftEntry(Base):
    __tablename__ = "drafts"
    id = Column(Integer, primary_key=True)
    type = Column(String)
    context = Column(Text)
    body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Инициализация LLM с клиентом
client = AsyncGroq(api_key="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")

app = FastAPI(title="Draft Helper API")

# Инициализация БД
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Зависимость для БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Модели Pydantic
class EmailRequest(BaseModel):
    to: str
    subject: str
    key_points: str

class PostRequest(BaseModel):
    topic: str
    keywords: str

class DraftResponse(BaseModel):
    id: int
    type: str
    context: str
    body: str
    created_at: datetime
    class Config:
        from_attributes = True

# Эндпоинты
@app.post("/draft/email", response_model=DraftResponse)
async def create_email_draft(req: EmailRequest, db: AsyncSession = Depends(get_db)):
    prompt = f"Напиши письмо для {req.to} на тему {req.subject}. Тезисы: {req.key_points}."
    
    completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты профессиональный помощник."},
            {"role": "user", "content": prompt}
        ]
    )
    generated_body = completion.choices[0].message.content
    
    new_draft = DraftEntry(type="Email", context=req.subject, body=generated_body)
    db.add(new_draft)
    await db.commit() 
    await db.refresh(new_draft)
    return new_draft

@app.post("/draft/post", response_model=DraftResponse)
async def create_post_draft(req: PostRequest, db: AsyncSession = Depends(get_db)):
    prompt = f"Напиши пост. Тема: {req.topic}. Ключи: {req.keywords}."
    
    completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты креативный блогер."},
            {"role": "user", "content": prompt}
        ]
    )
    generated_body = completion.choices[0].message.content
    
    new_draft = DraftEntry(type="Post", context=req.topic, body=generated_body)
    db.add(new_draft)
    await db.commit()
    await db.refresh(new_draft)
    return new_draft

@app.get("/drafts", response_model=List[DraftResponse])
async def get_all_drafts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DraftEntry).order_by(DraftEntry.created_at.desc()))
    return result.scalars().all()
