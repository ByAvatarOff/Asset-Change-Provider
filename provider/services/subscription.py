import logging
from typing import Dict, Optional

from provider.gateways.rabbitmq.producer import Producer
from provider.schemas.models import SubscribeRequest, UnsubscribeRequest
from provider.gateways.telegram.client import NotificationClient

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, client: NotificationClient, producer: Producer) -> None:
        self._client = client
        self._producer = producer

    async def subscribe_user(self, request: SubscribeRequest) -> bool:
        try:
            success = await self._send_command_to_aggregator(
                user_id=request.user_id, request=request, is_subscribe=True
            )
            if not success:
                logger.error(f"Failed to send subscribe command to aggregator for user {request.user_id}")
                return False

            success = await self._client.send_init_message(
                chat_id=request.user_id,
                symbols=request.symbols,
                timeframe=request.timeframe.value,
                thresholds=request.thresholds
            )

            if not success:
                logger.error(f"Failed to send init message to user {request.user_id}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error subscribing user {request.user_id}: {e}")
            return False

    async def unsubscribe_user(self, request: UnsubscribeRequest) -> bool:
        """Удаление подписки пользователя"""
        try:
            await self._send_command_to_aggregator(user_id=request.user_id, is_subscribe=False)
            logger.info(f"User {request.user_id} unsubscribed")
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing user {request.user_id}: {e}")
            return False

    async def _send_command_to_aggregator(
        self, user_id: str, request: SubscribeRequest | None = None, is_subscribe: bool = True
    ) -> bool:
        try:
            command_message = self._prepare_message_to_aggregator(
                user_id=user_id, request=request, is_subscribe=is_subscribe
            )
            await self._producer.produce(routing_key="commands", message=command_message)
            return True

        except Exception as e:
            logger.error(f"Error sending subscribe command to aggregator: {e}")
            return False

    @staticmethod
    def _prepare_message_to_aggregator(
        user_id: str, request: SubscribeRequest | None = None, is_subscribe: bool = True
    ) -> dict:
        if is_subscribe and request:
            return {
                "action": "subscribe",
                "user_id": user_id,
                "symbols": request.symbols,
                "thresholds": request.thresholds,
                "timeframe": request.timeframe.value
            }
        else:
            return {
                "action": "unsubscribe",
                "user_id": user_id
            }
