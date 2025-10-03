from pydantic import BaseModel
from typing import List, Optional

from provider.schemas.enums import TimeFrame


class SubscribeRequest(BaseModel):
    user_id: str
    symbols: List[str]
    thresholds: List[float]  # [0.5, 1.0, 2.0] - три уровня
    timeframe: TimeFrame


class UnsubscribeRequest(BaseModel):
    user_id: str


class SubscriptionResponse(BaseModel):
    success: bool
    message: str
    subscription_id: Optional[str] = None


class PriceChangeMessage(BaseModel):
    user_id: str
    symbol: str
    timeframe: str
    price_change_percent: float
    open_price: float
    close_price: float
    change_level: int