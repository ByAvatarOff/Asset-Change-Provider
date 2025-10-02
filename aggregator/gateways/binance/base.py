import json
import asyncio
import websockets
import logging
from abc import ABC, abstractmethod
from aggregator.core.settings import settings

logger = logging.getLogger(__name__)


class Client(ABC):
    @abstractmethod
    async def get_ticket_info(self, symbols: list[str], timeframe: str): ...


class BinanceClient(Client):
    def __init__(self, reconnect_delay: int = 5):
        self.reconnect_delay = reconnect_delay
        self.is_running = True

    async def get_ticket_info(self, symbols: list[str], timeframe: str):
        streams = [
            f"{symbol.lower()}@kline_{timeframe}"
            for symbol in symbols
        ]
        stream_url = f"{settings.BINANCE_BASE_WS_URL}stream?streams={'/'.join(streams)}"

        while self.is_running:
            try:
                async with websockets.connect(stream_url) as websocket:
                    logger.info(f"WebSocket connected for symbols: {symbols}")
                    async for message in websocket:
                        if not self.is_running:
                            break

                        data = json.loads(message)
                        stream = data.get("stream", "")
                        symbol = stream.split("@")[0].upper()

                        processed_message = self._handle_message(json.dumps(data["data"]), symbol, timeframe)
                        if processed_message:
                            yield processed_message

            except websockets.exceptions.ConnectionClosed:
                if self.is_running:
                    logger.warning(f"WebSocket connection closed, reconnecting in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                if self.is_running:
                    logger.error(f"WebSocket error: {e}, reconnecting in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)

    @staticmethod
    def _handle_message(message: str, symbol: str, timeframe: str) -> dict:
        try:
            data = json.loads(message)
            kline = data["k"]
            close_price = float(kline['c'])
            open_price = float(kline['o'])

            price_change_percent = ((close_price - open_price) / open_price) * 100

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "price_change_percent": round(price_change_percent, 4),
                "open_price": open_price,
                "close_price": close_price,
                "timestamp": kline['T'],
                "kline_start": kline['t'],
                "kline_end": kline['T']
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {}

    async def stop(self):
        """Остановка клиента"""
        self.is_running = False