from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import aio_pika
from datetime import datetime
import json
import logging
from enum import Enum
import openai
import os

app = FastAPI(title="Crypto News Aggregator", version="1.0.0")


# Модели данных
class NewsType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class NewsSource(str, Enum):
    COINDESK = "coindesk"
    COINTELEGRAPH = "cointelegraph"
    TWITTER = "twitter"
    REDDIT = "reddit"


class RawNews(BaseModel):
    title: str
    content: str
    source: NewsSource
    url: Optional[str] = None
    published_at: Optional[datetime] = None


class ClassifiedNews(BaseModel):
    id: str
    title: str
    content: str
    source: NewsSource
    news_type: NewsType
    confidence: float
    url: Optional[str] = None
    published_at: datetime
    classified_at: datetime


class RabbitMQManager:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(
                "amqp://guest:guest@localhost:5672/"
            )
            self.channel = await self.connection.channel()

            # Создаем exchange для новостей
            self.news_exchange = await self.channel.declare_exchange(
                'crypto_news',
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def publish_news(self, news: ClassifiedNews):
        try:
            routing_key = f"news.{news.news_type.value}.{news.source.value}"
            message_body = news.json()

            message = aio_pika.Message(
                message_body.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    'news_type': news.news_type.value,
                    'source': news.source.value,
                    'timestamp': news.classified_at.isoformat()
                }
            )

            await self.news_exchange.publish(message, routing_key=routing_key)
            logger.info(f"Published news with routing key: {routing_key}")

        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    async def close(self):
        if self.connection:
            await self.connection.close()


# AI News Classifier
class NewsClassifier:
    def __init__(self):
        # Инициализация OpenAI API (замените на ваш ключ)
        openai.api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")

    async def classify_news(self, news: RawNews) -> tuple[NewsType, float]:
        """
        Классифицирует новость с помощью AI
        Возвращает тип новости и уровень уверенности
        """
        try:
            prompt = f"""
            Classify the following cryptocurrency news as BULLISH, BEARISH, or NEUTRAL.
            Also provide a confidence score from 0.0 to 1.0.

            Title: {news.title}
            Content: {news.content[:500]}...

            Return only in this format:
            Classification: [BULLISH/BEARISH/NEUTRAL]
            Confidence: [0.0-1.0]
            """

            # Для демонстрации используем простую логику
            # В реальном проекте здесь будет вызов к OpenAI API
            content_lower = (news.title + " " + news.content).lower()

            bullish_keywords = ['moon', 'bull', 'rise', 'up', 'growth', 'adoption', 'positive', 'gain']
            bearish_keywords = ['crash', 'bear', 'fall', 'down', 'drop', 'negative', 'loss', 'dump']

            bullish_score = sum(1 for keyword in bullish_keywords if keyword in content_lower)
            bearish_score = sum(1 for keyword in bearish_keywords if keyword in content_lower)

            if bullish_score > bearish_score:
                return NewsType.BULLISH, min(0.9, 0.5 + bullish_score * 0.1)
            elif bearish_score > bullish_score:
                return NewsType.BEARISH, min(0.9, 0.5 + bearish_score * 0.1)
            else:
                return NewsType.NEUTRAL, 0.6

        except Exception as e:
            logger.error(f"Classification error: {e}")
            return NewsType.NEUTRAL, 0.3


# Глобальные переменные
rabbitmq_manager = RabbitMQManager()
news_classifier = NewsClassifier()


# События жизненного цикла приложения
@app.on_event("startup")
async def startup_event():
    await rabbitmq_manager.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await rabbitmq_manager.close()


# API endpoints
@app.post("/news/process", response_model=dict)
async def process_news(news: RawNews, background_tasks: BackgroundTasks):
    """Обрабатывает входящую новость"""
    try:
        # Классифицируем новость
        news_type, confidence = await news_classifier.classify_news(news)

        # Создаем классифицированную новость
        classified_news = ClassifiedNews(
            id=f"{news.source.value}_{datetime.now().timestamp()}",
            title=news.title,
            content=news.content,
            source=news.source,
            news_type=news_type,
            confidence=confidence,
            url=news.url,
            published_at=news.published_at or datetime.now(),
            classified_at=datetime.now()
        )

        # Отправляем в RabbitMQ асинхронно
        background_tasks.add_task(rabbitmq_manager.publish_news, classified_news)

        return {
            "status": "success",
            "news_id": classified_news.id,
            "classification": news_type.value,
            "confidence": confidence
        }

    except Exception as e:
        logger.error(f"Error processing news: {e}")
        raise HTTPException(status_code=500, detail="Failed to process news")


@app.post("/news/batch-process", response_model=dict)
async def batch_process_news(news_list: List[RawNews], background_tasks: BackgroundTasks):
    """Обрабатывает множество новостей"""
    processed_count = 0

    for news in news_list:
        try:
            news_type, confidence = await news_classifier.classify_news(news)

            classified_news = ClassifiedNews(
                id=f"{news.source.value}_{datetime.now().timestamp()}_{processed_count}",
                title=news.title,
                content=news.content,
                source=news.source,
                news_type=news_type,
                confidence=confidence,
                url=news.url,
                published_at=news.published_at or datetime.now(),
                classified_at=datetime.now()
            )

            background_tasks.add_task(rabbitmq_manager.publish_news, classified_news)
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing news item: {e}")
            continue

    return {
        "status": "success",
        "processed_count": processed_count,
        "total_count": len(news_list)
    }


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "service": "crypto-news-aggregator"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)