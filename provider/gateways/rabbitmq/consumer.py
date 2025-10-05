import asyncio
import json
import logging
from typing import Callable, Any
from abc import ABC, abstractmethod

from aio_pika import IncomingMessage

from provider.gateways.rabbitmq.base import RabbitMqConnector

logger = logging.getLogger(__name__)


class Consumer(ABC):
    @abstractmethod
    async def consume(self, command: Callable, queue: str) -> None: ...

    @abstractmethod
    async def decode_message(self, message: Any) -> dict: ...

    @abstractmethod
    async def stop_consuming(self) -> None: ...


class RabbitMqConsumer(Consumer):
    def __init__(self, connector: RabbitMqConnector):
        self.connector = connector
        self._is_consuming = False
        self._consuming_task = None

    async def consume(self, command: Callable, queue: str) -> None:
        if self._is_consuming:
            logger.warning(f"Consumer for {queue} is already running")
            return

        self._is_consuming = True

        try:
            rabbit_queue = await self.connector.channel.get_queue(queue)

            async def message_handler(message: IncomingMessage):
                try:
                    decoded_message = await self.decode_message(message)
                    await command(decoded_message)
                except Exception as e:
                    logger.error(f"Error in message handler for {queue}: {e}")
                    await message.nack()

            await rabbit_queue.consume(message_handler)
            logger.info(f"✅ Registered consumer for queue: {queue}")

        except asyncio.CancelledError:
            logger.info(f"Consuming from {queue} cancelled")
        except Exception as e:
            logger.error(f"Error in consume for {queue}: {e}")
            raise

    async def decode_message(self, message: IncomingMessage) -> dict:
        """Декодирование сообщения"""
        try:
            async with message.process():
                decoded = json.loads(message.body.decode())
                logger.debug(f"Received message from queue: {decoded}")
                return decoded
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error decoding message: {e}")
            return {}

    async def stop_consuming(self):
        """Остановка потребления сообщений"""
        self._is_consuming = False
        logger.info("Stopped consuming from all queues")