import os
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from groq import Groq

# Настройки Базы Данных (SQLite)
DATABASE_URL = "sqlite:///./drafts.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DraftEntry(Base):
    __tablename__ = "drafts"
    id = Column(Integer, primary_key=True)
    type = Column(String)    # Email или Post
    context = Column(Text)   # Тема или краткое описание
    body = Column(Text)      # Сгенерированный текст
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Инициализация LLM с ключом 
# Ключ вставлен напрямую для максимальной простоты запуска
client = Groq(api_key="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")

# Описание моделей данных (для Swagger)

class EmailRequest(BaseModel):
    to: str = Field(..., title="Получатель", example="Коллега")
    subject: str = Field(..., title="Тема письма", example="Отчет по проекту")
    key_points: str = Field(..., title="Ключевые мысли", example="Все готово, пришлю в ПН")

class PostRequest(BaseModel):
    topic: str = Field(..., title="Тема поста", example="Плюсы изучения Python")
    keywords: str = Field(..., title="Ключевые слова", example="карьера, простота, разработка")

class DraftResponse(BaseModel):
    id: int
    type: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True

# Настройка FastAPI приложения
app = FastAPI(
    title="API 'Генератор черновиков'",
    description="Сервис для автоматического создания текстов писем и постов на русском языке",
    version="1.1.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Эндпоинты API

@app.post("/draft/email", response_model=DraftResponse, tags=["Генерация"], summary="Создать черновик письма")
def create_email_draft(req: EmailRequest, db: Session = Depends(get_db)):
    """Генерирует текст письма и сохраняет в БД."""
    prompt = f"Напиши email на русском. Кому: {req.to}. Тема: {req.subject}. Тезисы: {req.key_points}."
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты профессиональный помощник. Пиши грамотно и вежливо на русском языке."},
            {"role": "user", "content": prompt}
        ]
    )
    generated_body = completion.choices[0].message.content
    
    new_draft = DraftEntry(type="Email", context=req.subject, body=generated_body)
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)
    return new_draft

@app.post("/draft/post", response_model=DraftResponse, tags=["Генерация"], summary="Создать пост для блога")
def create_post_draft(req: PostRequest, db: Session = Depends(get_db)):
    """Генерирует текст поста и сохраняет в БД."""
    prompt = f"Напиши пост для блога на русском. Тема: {req.topic}. Ключевые слова: {req.keywords}."
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты креативный блогер. Пиши вовлекающе на русском языке."},
            {"role": "user", "content": prompt}
        ]
    )
    generated_body = completion.choices[0].message.content
    
    new_draft = DraftEntry(type="Post", context=req.topic, body=generated_body)
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)
    return new_draft

@app.get("/drafts", response_model=List[DraftResponse], tags=["Архив"], summary="Получить историю черновиков")
def get_all_drafts(db: Session = Depends(get_db)):
    """Возвращает список всех ранее созданных черновиков."""
    return db.query(DraftEntry).all()
