import telegram
import logging


from provider.core.settings import settings

logger = logging.getLogger(__name__)


class TelegramBotManager:
    def __init__(self):
        self.bot = None
        self.broadcast_configs = {}

    async def initialize(self):
        """Инициализация Telegram бота"""
        try:
            self.bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
            # Проверяем подключение
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot initialized: {bot_info.username}")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            raise

    def add_broadcast_config(self, config):
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