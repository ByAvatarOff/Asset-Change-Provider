from pydantic import BaseModel, Field
from enum import Enum


class ActionEnum(str, Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


class InputCommand(BaseModel):
    action: ActionEnum
    user_id: str
    symbols: list[str] = Field(default_factory=list)
    timeframe: str | None = None
    thresholds: list[float] = Field(default_factory=list)


class PriceChangeMessage(BaseModel):
    user_id: str | None = None
    symbol: str
    timeframe: str
    price_change_percent: float
    open_price: float
    close_price: float
    change_level: int | None = None