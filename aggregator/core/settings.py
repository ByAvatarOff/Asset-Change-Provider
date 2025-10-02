from functools import cache


class Settings:
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_URL: str

    BINANCE_BASE_WS_URL: str = "wss://stream.binance.com:9443/"

    class Config:
        case_sensitive = True
        env_file = ".env"


@cache
def get_settings():
    return Settings()


settings = get_settings()