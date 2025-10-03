import logging
import asyncio


from provider.gateways.rabbitmq.consumer import Consumer, RabbitMqConsumer
from provider.gateways.rabbitmq.base import RabbitMqConnector
from provider.core.settings import settings
from provider.services.notification import NotificationService

logger = logging.getLogger(__name__)


class PriceConsumerProcessor:
    def __init__(self, connector: RabbitMqConnector, notification_service: NotificationService):
        self._connector = connector
        self._notification_service = notification_service
        self.is_running = False
        self._consumers: list[Consumer] = []

    async def start_consumers(self) -> None:
        queues = [
            settings.PRICE_CHANGE_QUEUE_LEVEL_1,
            settings.PRICE_CHANGE_QUEUE_LEVEL_2,
            settings.PRICE_CHANGE_QUEUE_LEVEL_3
        ]

        for queue in queues:
            logger.info(f"Creating consumer for queue: {queue}")
            consumer = RabbitMqConsumer(self._connector)
            self._consumers.append(consumer)

            await consumer.consume(
                command=lambda msg: self._notification_service.process_price_change(msg, queue),
                queue=queue
            )
            logger.info(f"✅ Consumer for {queue} started")

    async def start(self) -> None:
        self.is_running = True
        logger.info("Starting Notification Processor...")
        try:
            await self.start_consumers()
            logger.info("✅ All consumers started successfully")

            # Основной цикл
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error starting notification processor: {e}")
            raise

    async def stop(self) -> None:
        self.is_running = False
        logger.info("Stopping all consumers...")

        for consumer in self._consumers:
            await consumer.stop_consuming()

        logger.info("✅ All consumers stopped")