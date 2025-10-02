from functools import cache


class Settings:
    TELEGRAM_BOT_TOKEN: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"


@cache
def get_settings():
    return Settings()


settings = get_settings()