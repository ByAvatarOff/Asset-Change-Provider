from fastapi.params import Depends

from provider.gateways.rabbitmq.producer import Producer, RabbitMqProducer
from provider.gateways.rabbitmq.base import RabbitMqConnector
from provider.gateways.telegram.client import TelegramClient, NotificationClient
from provider.services.subscription import SubscriptionService


def resolve_connector() -> RabbitMqConnector:
    return RabbitMqConnector()


def resolve_telegram_client() -> TelegramClient:
    return TelegramClient()


def resolve_producer(connector: RabbitMqConnector = Depends(resolve_connector)) -> RabbitMqProducer:
    return RabbitMqProducer(connector=connector)


def resolve_subscribe_service(
    client: NotificationClient = Depends(resolve_telegram_client),
    producer: Producer = Depends(resolve_producer),
) -> SubscriptionService:
    return SubscriptionService(client=client, producer=producer)