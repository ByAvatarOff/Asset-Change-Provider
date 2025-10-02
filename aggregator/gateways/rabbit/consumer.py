import asyncio
import json
import logging
from typing import Callable, Any
from abc import ABC, abstractmethod

from aio_pika import IncomingMessage

from gateways.rabbit.base import RabbitMqConnector

logger = logging.getLogger(__name__)


class Consumer(ABC):
    @abstractmethod
    async def consume(self, command: Callable, queue: str) -> None: ...

    @abstractmethod
    async def decode_message(self, message: Any) -> dict: ...


class RabbitMqConsumer(Consumer):
    def __init__(self, connector: RabbitMqConnector):
        self.connector = connector
        self._is_consuming = False

    async def consume(self, command: Callable, queue: str) -> None:
        """Запуск потребления сообщений с использованием существующего соединения"""
        self._is_consuming = True

        try:
            # Используем существующее соединение из connector
            rabbit_queue = await self.connector.channel.get_queue(queue)
            await rabbit_queue.consume(self._create_message_handler(command))
            logger.info(f"Started consuming from queue: {queue}")

            # Бесконечный цикл для поддержания консьюмера активным
            while self._is_consuming:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Consuming cancelled")
        except Exception as e:
            logger.error(f"Error in consume loop: {e}")
            raise

    def _create_message_handler(self, command: Callable) -> Callable:
        """Создает обработчик сообщений с правильной сигнатурой"""

        async def message_handler(message: IncomingMessage) -> None:
            try:
                decoded_message = await self.decode_message(message)
                await command(decoded_message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
                await message.nack()

        return message_handler

    async def decode_message(self, message: IncomingMessage) -> dict:
        """Декодирование сообщения"""
        try:
            async with message.process():
                decoded = json.loads(message.body.decode())
                logger.debug(f"Received message: {decoded}")
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