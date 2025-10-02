import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from aggregator.core.settings import settings

import aio_pika

logger = logging.getLogger(__name__)


class RabbitMqConnector:
    def __init__(self):
        self._connection = None
        self.channel = None
        self.exchanger = None

    async def connect(self) -> None:
        """Установка соединения с RabbitMQ"""
        try:
            if self._connection is None or self._connection.is_closed:
                self._connection = await aio_pika.connect_robust("amqp://guest:guest@rabbitmq:5672/")
                self.channel = await self._connection.channel()
                self.exchanger = await self.channel.get_exchange("price_changes")
                logger.info("Successfully connected to RabbitMQ")
        except Exception as e:
            logger.exception(f"Failed to connect to RabbitMQ: {e}")
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()

            if self._connection and not self._connection.is_closed:
                await self._connection.close()

            self.channel = None
            self._connection = None
            self.exchanger = None
            logger.info("Disconnected from RabbitMQ")

        except Exception as e:
            logger.exception(f"Error during RabbitMQ disconnect: {e}")

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator["RabbitMqConnector", None]:
        """Контекстный менеджер для всего соединения"""
        try:
            await self.connect()
            yield self
        except Exception as e:
            logger.exception(f"Error in connection context: {e}")
            raise
        finally:
            await self.disconnect()

    async def is_connected(self) -> bool:
        """Проверка активности соединения"""
        return (
            self._connection is not None and
            not self._connection.is_closed and
            self.exchanger is not None
        )