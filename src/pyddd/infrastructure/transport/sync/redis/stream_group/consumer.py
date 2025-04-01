from redis import Redis

from pyddd.application.abstractions import IApplication
from pyddd.infrastructure.transport.core.abstractions import (
    IMessageConsumer,
    IEventFactory,
)
from pyddd.infrastructure.transport.core.event_factory import UniversalEventFactory
from pyddd.infrastructure.transport.core.tracker_factory import NotificationTrackerFactory
from pyddd.infrastructure.transport.sync.domain import (
    INotificationQueue,
    IAskPolicy,
    DefaultAskPolicy,
    NotificationQueue,
    MessageConsumer,
)
from pyddd.infrastructure.transport.sync.redis import (
    GroupStreamHandler,
    RedisStreamTrackerStrategy,
)


class RedisStreamGroupConsumer(IMessageConsumer):
    """
    Фасад для упрощения сборки консюмера
    """

    def __init__(
            self,
            redis: Redis,
            group_name: str,
            consumer_name: str,
            queue: INotificationQueue = None,
            event_factory: IEventFactory = None,
            ask_policy: IAskPolicy = None,
            block_ms: int = None,
    ):
        self._ask_policy = ask_policy or DefaultAskPolicy()
        self._event_factory = event_factory or UniversalEventFactory()
        self._queue = queue or NotificationQueue(
            message_handler=GroupStreamHandler(
                group_name=group_name,
                consumer_name=consumer_name,
                client=redis,
                block=block_ms,
                tracker_factory=NotificationTrackerFactory(strategy=RedisStreamTrackerStrategy())
            )
        )
        self._consumer = MessageConsumer(
            queue=self._queue,
            event_factory=self._event_factory,
            ask_policy=self._ask_policy
        )

    def subscribe(self, topic: str):
        return self._consumer.subscribe(topic)

    def set_application(self, application: IApplication):
        return self._consumer.set_application(application)

    @property
    def ask_policy(self):
        return self._ask_policy

    @property
    def event_factory(self):
        return self._event_factory

    @property
    def queue(self):
        return self._queue
