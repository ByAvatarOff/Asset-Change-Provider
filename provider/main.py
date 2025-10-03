import logging
import asyncio
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager

from provider.gateways.rabbitmq.base import RabbitMqConnector
from provider.gateways.rabbitmq.consumer import RabbitMqConsumer
from provider.gateways.telegram.client import TelegramClient
from provider.core.price_processor import PriceConsumerProcessor
from provider.api.utils import router as api_router
from provider.services.notification import NotificationService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

connector = None
processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global connector, processor

    try:
        connector = RabbitMqConnector()
        await connector.connect()
        logger.info("✅ RabbitMQ connector initialized")

        notification_service = NotificationService(client=TelegramClient())

        processor = PriceConsumerProcessor(
            connector=connector,
            notification_service=notification_service
        )

        asyncio.create_task(processor.start())
        logger.info("✅ Price processor started in background")

    except Exception as e:
        logger.error(f"❌ Failed to initialize application components: {e}")

    yield

    try:
        if processor:
            await processor.stop()
    except Exception as e:
        logger.error(f"Error stopping processor: {e}")

    try:
        if connector:
            await connector.disconnect()
    except Exception as e:
        logger.error(f"Error disconnecting RabbitMQ: {e}")


app = FastAPI(
    title="Notification Provider API",
    description="API для управления подписками на уведомления об изменении цен",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router)
