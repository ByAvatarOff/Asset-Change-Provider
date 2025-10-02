import logging
import json
from abc import ABC, abstractmethod

import aio_pika
from gateways.rabbit.base import RabbitMqConnector

logger = logging.getLogger(__name__)


class Producer(ABC):
    @abstractmethod
    async def produce(self, routing_key: str, message: dict) -> None: ...


class RabbitMqProducer(Producer):
    def __init__(self, connector: RabbitMqConnector):
        self._connector = connector

    async def produce(self, routing_key: str, message: dict) -> None:
        """Отправка сообщения в указанную очередь"""
        try:
            await self._connector.exchanger.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=routing_key
            )
            logger.debug(f"Message sent to {routing_key}: {message}")

        except Exception as e:
            logger.exception(f"Failed to send message to {routing_key}: {e}")
            raise

    async def produce_without_context(self, routing_key: str, message: dict) -> None:
        """Альтернативный метод без контекстного менеджера (для частых отправок)"""
        if not await self.is_connected():
            await self.connect()

        try:
            await self.exchanger.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=routing_key
            )
            logger.debug(f"Message sent to {routing_key}")
        except Exception as e:
            logger.exception(f"Failed to send message to {routing_key}: {e}")
            await self.disconnect()
            raise