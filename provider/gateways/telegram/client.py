import logging
from abc import ABC, abstractmethod

from telegram import Bot
from telegram.error import TelegramError

from provider.core.settings import settings

logger = logging.getLogger(__name__)


class NotificationClient(ABC):
    @abstractmethod
    async def send_message(self, chat_id: str, message: str) -> bool: ...

    @abstractmethod
    async def send_init_message(
self, chat_id: str, symbols: list[str], timeframe: str, thresholds: list[float]
    ) -> bool: ...

    @abstractmethod
    async def send_message_with_buttons(self, chat_id: str, message: str, buttons: list[list[str]]) -> bool: ...


class TelegramClient(NotificationClient):
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async def send_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True

        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_init_message(
        self, chat_id: str, symbols: list[str], timeframe: str, thresholds: list[float]
    ) -> bool:
        message = settings.INIT_MESSAGE.format(
            symbols=", ".join(symbols),
            timeframe=timeframe,
            thresholds=", ".join(str(t) for t in thresholds)
        )
        return await self.send_message(chat_id, message)

    async def send_message_with_buttons(self, chat_id: str, message: str, buttons: list[list[str]]) -> bool:
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            keyboard = []
            for row in buttons:
                keyboard_row = []
                for button_text in row:
                    keyboard_row.append(InlineKeyboardButton(button_text, callback_data=button_text))
                keyboard.append(keyboard_row)

            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send message with buttons: {e}")
            return False
