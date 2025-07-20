# main.py
import datetime
import sqlite3
from typing import List, Optional
import re

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# создаем экземпляр fastapi приложения
app = FastAPI()

# настройки базы данных
DATABASE_URL = "reviews.db"

# словарь для анализа тональности

SENTIMENT_PATTERNS = {
    "positive": re.compile(r'хорош|люблю', re.IGNORECASE),
    "negative": re.compile(r'плохо|ненавиж', re.IGNORECASE)
}

# модели данных
class ReviewCreate(BaseModel):
    text: str  # модель для создания отзыва (только текст)

class Review(BaseModel):
    id: int  # id отзыва
    text: str  # текст отзыва
    sentiment: str  # тональность
    created_at: str  # дата создания

# функция для создания таблицы в бд
def create_table():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL,
          sentiment TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

# вызываем создание таблицы при старте
create_table()

# функция для определения тональности текста
def analyze_sentiment(text: str) -> str:
    for sentiment, pattern in SENTIMENT_PATTERNS.items():
        if pattern.search(text):
            return sentiment
    return "neutral"

# endpoint для создания отзыва
@app.post("/reviews", response_model=Review)
async def create_review(review_data: ReviewCreate):
    # получаем данные из запроса
    text = review_data.text
    # определяем тональность
    sentiment = analyze_sentiment(text)
    # получаем текущее время
    created_at = datetime.datetime.utcnow().isoformat()

    # подключаемся к бд
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    # вставляем новый отзыв
    cursor.execute("""
        INSERT INTO reviews (text, sentiment, created_at)
        VALUES (?, ?, ?)
    """, (text, sentiment, created_at))
    # получаем id созданного отзыва
    review_id = cursor.lastrowid
    conn.commit()

    # получаем созданный отзыв из бд
    cursor.execute("""
        SELECT id, text, sentiment, created_at
        FROM reviews
        WHERE id = ?
    """, (review_id,))
    row = cursor.fetchone()
    conn.close()

    # если отзыв найден - возвращаем его
    if row:
        review = Review(id=row[0], text=row[1], sentiment=row[2], created_at=row[3])
        return review
    else:
        # если не найден - возвращаем ошибку
        raise HTTPException(status_code=500, detail="не удалось получить отзыв")

# endpoint для получения отзывов
@app.get("/reviews", response_model=List[Review])
async def get_reviews(sentiment: Optional[str] = Query(None)):
    # подключаемся к бд
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    # если указана тональность - фильтруем по ней
    if sentiment:
        cursor.execute("""
            SELECT id, text, sentiment, created_at
            FROM reviews
            WHERE sentiment = ?
        """, (sentiment,))
    else:
        # если не указана - получаем все отзывы
        cursor.execute("""
            SELECT id, text, sentiment, created_at
            FROM reviews
        """)

    # получаем все найденные отзывы
    rows = cursor.fetchall()
    conn.close()

    # преобразуем результат в список моделей Review
    reviews = [Review(id=row[0], text=row[1], sentiment=row[2], created_at=row[3]) for row in rows]
    return reviews