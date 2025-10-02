import asyncio
import logging
import signal

from gateways.binance.base import Client, BinanceClient
from gateways.rabbit.base import RabbitMqConnector
from gateways.rabbit.consumer import Consumer, RabbitMqConsumer
from gateways.rabbit.producer import Producer, RabbitMqProducer

logger = logging.getLogger(__name__)


class MainService:
    def __init__(self, consumer: Consumer, producer: Producer, client: Client) -> None:
        self._producer = producer
        self._consumer = consumer
        self._client = client

        self.active_connections: dict[str, asyncio.Task] = {}
        self.user_subscriptions: dict[str, set[str]] = {}
        self.is_running = True

    async def process_command(self, message: dict) -> None:
        try:
            user_id = message.get('user_id')
            symbols = message.get('symbols', [])
            thresholds = message.get('thresholds', [])  # TODO use
            timeframe = message.get('timeframe', '1m')

            await self.subscribe_user(user_id, symbols, timeframe, thresholds)
            logger.info(f"Subscribed user {user_id} to {symbols}")

        except Exception as e:
            logger.error(f"Error processing command: {e}")

    async def send_ticker_info(self, user_id: str, symbols: list[str], timeframe: str, thresholds: list[float]) -> None:
        """Отправка информации о тикерах для конкретного пользователя"""
        try:
            async for message in self._client.get_ticket_info(symbols=symbols, timeframe=timeframe):
                logger.info(
                    f"Start get message {message}"
                )
                if not message:  # Пропускаем пустые сообщения
                    continue

                # TODO: Реализовать логику определения уровня на основе thresholds
                change_level = self._calculate_change_level(message['price_change_percent'], thresholds)
                routing_key = f"level_{change_level}"

                # Добавляем user_id в сообщение
                message['user_id'] = user_id
                message['change_level'] = change_level

                await self._producer.produce(routing_key=routing_key, message=message)
                logger.info(
                    f"Sent {message['symbol']} change {message['price_change_percent']:.2f}% to level {change_level}"
                )

        except Exception as e:
            logger.error(f"Error in send_ticker_info for user {user_id}: {e}")

    def _calculate_change_level(self, change_percent: float, thresholds: list[float]) -> int:
        """Определение уровня изменения на основе порогов"""
        change_abs = abs(change_percent)
        for level, threshold in enumerate(thresholds, 1):
            if change_abs >= threshold:
                return level
        return 0

    async def subscribe_user(self, user_id: str, symbols: list[str], timeframe: str, thresholds: list[float]) -> None:
        await self.unsubscribe_user(user_id)

        if not symbols:
            logger.error(f"No symbols provided for user {user_id}")
            return

        task = asyncio.create_task(
            self.send_ticker_info(user_id=user_id, symbols=symbols, timeframe=timeframe, thresholds=thresholds)
        )
        self.active_connections[user_id] = task
        self.user_subscriptions[user_id] = set(symbols)
        logger.info(f"Started WebSocket monitoring for user {user_id}: {symbols}")

    async def unsubscribe_user(self, user_id: str) -> None:
        if user_id in self.active_connections:
            task = self.active_connections[user_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Task for user {user_id} cancelled")
                except Exception as e:
                    logger.error(f"Error cancelling task for user {user_id}: {e}")

            del self.active_connections[user_id]
            if user_id in self.user_subscriptions:
                del self.user_subscriptions[user_id]

            logger.info(f"Unsubscribed user {user_id}")

    async def start(self):
        """Запуск сервиса"""
        logger.info("Starting MainService...")
        # Запускаем потребителя в отдельной задаче
        consume_task = asyncio.create_task(
            self._consumer.consume(command=self.process_command, queue="commands")
        )

        try:
            while self.is_running:
                await asyncio.sleep(1)
        finally:
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass

    async def stop(self):
        logger.info("Stopping MainService...")
        self.is_running = False

        # Останавливаем binance client
        if hasattr(self._client, 'stop'):
            await self._client.stop()

        # Отписываем всех пользователей
        for user_id in list(self.active_connections.keys()):
            await self.unsubscribe_user(user_id)

        await self._consumer.disconnect()
        await self._producer.disconnect()
        logger.info("MainService stopped")


async def main():
    connector = RabbitMqConnector()
    await connector.connect()

    service = MainService(
        consumer=RabbitMqConsumer(connector=connector),
        producer=RabbitMqProducer(connector=connector),
        client=BinanceClient()
    )

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
    finally:
        if service.is_running:
            await service.stop()


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())