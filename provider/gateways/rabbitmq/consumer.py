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
