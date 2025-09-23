from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import aio_pika
from datetime import datetime
import json
import logging
from enum import Enum
import telegram
from telegram.ext import Application
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Crypto News Broadcaster", version="1.0.0")


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


class BroadcastConfig(BaseModel):
    chat_id: str
    chat_name: str
    news_types: List[NewsType]
    sources: List[NewsSource]
    min_confidence: float = 0.5
    active: bool = True


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


# Telegram Bot Manager
class TelegramBotManager:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "your-bot-token-here")
        self.bot = None
        self.broadcast_configs: Dict[str, BroadcastConfig] = {}

    async def initialize(self):
        """Инициализация Telegram бота"""
        try:
            self.bot = telegram.Bot(token=self.bot_token)
            # Проверяем подключение
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot initialized: {bot_info.username}")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise

    def add_broadcast_config(self, config: BroadcastConfig):
        """Добавляет конфигурацию для трансляции"""
        self.broadcast_configs[config.chat_id] = config
        logger.info(f"Added broadcast config for chat: {config.chat_name}")

    def remove_broadcast_config(self, chat_id: str):
        """Удаляет конфигурацию трансляции"""
        if chat_id in self.broadcast_configs:
            del self.broadcast_configs[chat_id]
            logger.info(f"Removed broadcast config for chat: {chat_id}")

    async def send_news(self, news: ClassifiedNews):
        """Отправляет новость в соответствующие чаты"""
        if not self.bot:
            logger.error("Telegram bot not initialized")
            return

        sent_count = 0
        for chat_id, config in self.broadcast_configs.items():
            if not config.active:
                continue

            # Проверяем соответствие конфигурации
            if (news.news_type in config.news_types and
                    news.source in config.sources and
                    news.confidence >= config.min_confidence):

                try:
                    message = self._format_news_message(news)
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    sent_count += 1
                    logger.info(f"Sent news {news.id} to chat {config.chat_name}")

                except Exception as e:
                    logger.error(f"Failed to send message to {chat_id}: {e}")

        logger.info(f"News {news.id} sent to {sent_count} chats")

    def _format_news_message(self, news: ClassifiedNews) -> str:
        """Форматирует сообщение для Telegram"""
        emoji_map = {
            NewsType.BULLISH: "🚀",
            NewsType.BEARISH: "🐻",
            NewsType.NEUTRAL: "📊"
        }

        emoji = emoji_map.get(news.news_type, "📰")
        confidence_percent = int(news.confidence * 100)

        message = f"{emoji} <b>{news.title}</b>\n\n"

        # Ограничиваем длину контента
        content = news.content[:300] + "..." if len(news.content) > 300 else news.content
        message += f"{content}\n\n"

        message += f"📈 Тип: <b>{news.news_type.value.upper()}</b>\n"
        message += f"🎯 Уверенность: <b>{confidence_percent}%</b>\n"
        message += f"📱 Источник: <b>{news.source.value.upper()}</b>\n"

        if news.url:
            message += f"\n🔗 <a href='{news.url}'>Читать полностью</a>"

        return message


# RabbitMQ Consumer Manager
class RabbitMQConsumer:
    def __init__(self, telegram_manager: TelegramBotManager):
        self.connection = None
        self.channel = None
        self.telegram_manager = telegram_manager

    async def connect(self):
        """Подключение к RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(
                "amqp://guest:guest@localhost:5672/"
            )
            self.channel = await self.connection.channel()

            # Получаем exchange
            self.news_exchange = await self.channel.declare_exchange(
                'crypto_news',
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def start_consuming(self):
        """Запуск потребителей для разных типов новостей"""
        try:
            # Создаем очереди для разных типов новостей
            await self._setup_queue_consumer("bullish_news", "news.bullish.*")
            await self._setup_queue_consumer("bearish_news", "news.bearish.*")
            await self._setup_queue_consumer("neutral_news", "news.neutral.*")

            logger.info("Started consuming messages from RabbitMQ")

        except Exception as e:
            logger.error(f"Failed to start consuming: {e}")
            raise

    async def _setup_queue_consumer(self, queue_name: str, routing_key: str):
        """Настройка очереди и обработчика"""
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True
        )

        await queue.bind(self.news_exchange, routing_key)

        async def process_message(message):
            async with message.process():
                try:
                    news_data = json.loads(message.body.decode())
                    news = ClassifiedNews(**news_data)

                    logger.info(f"Processing news: {news.id} ({news.news_type.value})")
                    await self.telegram_manager.send_news(news)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # В реальном проекте здесь может быть логика повторных попыток

        await queue.consume(process_message)
        logger.info(f"Queue consumer setup: {queue_name} -> {routing_key}")

    async def close(self):
        """Закрытие соединения"""
        if self.connection:
            await self.connection.close()


# Глобальные переменные
telegram_manager = TelegramBotManager()
rabbitmq_consumer = RabbitMQConsumer(telegram_manager)


# События жизненного цикла приложения
@app.on_event("startup")
async def startup_event():
    await telegram_manager.initialize()
    await rabbitmq_consumer.connect()

    # Запуск потребителя в фоновом режиме
    asyncio.create_task(rabbitmq_consumer.start_consuming())


@app.on_event("shutdown")
async def shutdown_event():
    await rabbitmq_consumer.close()


# API endpoints
@app.post("/broadcast/config", response_model=dict)
async def add_broadcast_config(config: BroadcastConfig):
    """Добавляет конфигурацию для трансляции"""
    try:
        telegram_manager.add_broadcast_config(config)
        return {
            "status": "success",
            "message": f"Broadcast config added for chat: {config.chat_name}"
        }
    except Exception as e:
        logger.error(f"Error adding broadcast config: {e}")
        raise HTTPException(status_code=500, detail="Failed to add broadcast config")


@app.get("/broadcast/configs", response_model=Dict[str, BroadcastConfig])
async def get_broadcast_configs():
    """Получает все конфигурации трансляции"""
    return telegram_manager.broadcast_configs


@app.delete("/broadcast/config/{chat_id}", response_model=dict)
async def remove_broadcast_config(chat_id: str):
    """Удаляет конфигурацию трансляции"""
    try:
        telegram_manager.remove_broadcast_config(chat_id)
        return {
            "status": "success",
            "message": f"Broadcast config removed for chat: {chat_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Chat configuration not found")


@app.put("/broadcast/config/{chat_id}/toggle", response_model=dict)
async def toggle_broadcast_config(chat_id: str):
    """Включает/выключает конфигурацию трансляции"""
    if chat_id not in telegram_manager.broadcast_configs:
        raise HTTPException(status_code=404, detail="Chat configuration not found")

    config = telegram_manager.broadcast_configs[chat_id]
    config.active = not config.active

    return {
        "status": "success",
        "chat_id": chat_id,
        "active": config.active
    }


@app.post("/broadcast/test-message", response_model=dict)
async def send_test_message(chat_id: str, message: str):
    """Отправляет тестовое сообщение в чат"""
    try:
        await telegram_manager.bot.send_message(
            chat_id=chat_id,
            text=f"🧪 Test message: {message}",
            parse_mode='HTML'
        )
        return {
            "status": "success",
            "message": "Test message sent successfully"
        }
    except Exception as e:
        logger.error(f"Failed to send test message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test message")


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "service": "crypto-news-broadcaster",
        "active_configs": len(telegram_manager.broadcast_configs)
    }


@app.get("/stats")
async def get_stats():
    """Получает статистику сервиса"""
    active_configs = sum(1 for config in telegram_manager.broadcast_configs.values() if config.active)

    return {
        "total_configs": len(telegram_manager.broadcast_configs),
        "active_configs": active_configs,
        "inactive_configs": len(telegram_manager.broadcast_configs) - active_configs,
        "bot_status": "active" if telegram_manager.bot else "inactive"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)