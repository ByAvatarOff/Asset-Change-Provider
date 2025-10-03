from functools import cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    TELEGRAM_BOT_TOKEN: str

    PRICE_CHANGE_QUEUE_LEVEL_1: str = "price_change_level_1"
    PRICE_CHANGE_QUEUE_LEVEL_2: str = "price_change_level_2"
    PRICE_CHANGE_QUEUE_LEVEL_3: str = "price_change_level_3"

    LEVEL_1_MESSAGE: str = "🔔 Небольшое изменение цены {symbol}: {change_percent:.2f}%"
    LEVEL_2_MESSAGE: str = "⚠️ Значительное изменение цены {symbol}: {change_percent:.2f}%"
    LEVEL_3_MESSAGE: str = "🚨 КРИТИЧЕСКОЕ изменение цены {symbol}: {change_percent:.2f}%"

    INIT_MESSAGE: str = """
    📊 <b>Ваша подписка активирована!</b>
    💎 <b>Мониторим пары:</b> {symbols}
    ⏰ <b>Таймфрейм:</b>: {timeframe}
    <b>Пороги уведомлений:</b>: {thresholds}%
    🚀 <b>Будем уведомлять вас о значительных изменениях цен.</b>
    """

    class Config:
        case_sensitive = True
        env_file = ".env"


@cache
def get_settings():
    return Settings()


settings = get_settings()