import logging

from provider.gateways.telegram.client import NotificationClient
from provider.schemas.models import PriceChangeMessage
from provider.core.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, client: NotificationClient):
        self._client = client
        self.is_running = False

    async def process_price_change(self, message_data: dict, *args, **kwargs) -> None:
        price_change = PriceChangeMessage(**message_data)
        try:
            message_text, buttons = self._format_notification_message(price_change)
            if buttons:
                await self._client.send_message_with_buttons(
                    price_change.user_id, message_text, buttons
                )
            else:
                await self._client.send_message(
                    price_change.user_id, message_text
                )
        except Exception as e:
            logger.error(f"Error processing price change notification: {e}")

    @staticmethod
    def _format_notification_message(price_change: PriceChangeMessage):
        if price_change.change_level == 1:
            template = settings.LEVEL_1_MESSAGE
            emoji = "🔔"
        elif price_change.change_level == 2:
            template = settings.LEVEL_2_MESSAGE
            emoji = "⚠️"
        else:
            template = settings.LEVEL_3_MESSAGE
            emoji = "🚨"

        change_direction = "📈" if price_change.price_change_percent > 0 else "📉"
        change_emoji = "🟢" if price_change.price_change_percent > 0 else "🔴"

        base_message = template.format(
            symbol=price_change.symbol,
            change_percent=abs(price_change.price_change_percent),
            open_price=price_change.open_price,
            close_price=price_change.close_price
        )

        message_text = f"""
        {emoji} {change_direction} <b>Уведомление о изменении цены</b>
        
        {base_message}
        
        💎 <b>Уровень:</b> {price_change.change_level}
        💰 <b>Цена открытия:</b> {price_change.open_price:,.2f}
        💰 <b>Цена закрытия:</b> {price_change.close_price:,.2f}
        {change_emoji} <b>Изменение:</b> {price_change.price_change_percent:+.2f}%
        """

        buttons = []
        if price_change.change_level >= 2:
            buttons = [
                ["📈 График", "🔍 Детали"],
                ["🔕 Отключить уведомления"]
            ]

        return message_text, buttons

    async def send_quick_chart(self, chat_id: str, symbol: str) -> bool:
        """Отправка быстрой ссылки на график"""
        chart_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
        message = f"📊 <b>График {symbol}</b>\n\n{chart_url}"
        return await self._client.send_message(chat_id, message)