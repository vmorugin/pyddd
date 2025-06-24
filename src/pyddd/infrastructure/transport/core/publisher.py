import typing as t
import uuid
from functools import partial

from pyddd.application.abstractions import (
    IModule,
    AnyCallable,
)
from pyddd.domain.abstractions import (
    IMessage,
)
from pyddd.infrastructure.transport.core.abstractions import (
    PublisherProtocol,
)


class EventPublisherModule(IModule):
    def __init__(self, publisher: PublisherProtocol):
        self._publisher = publisher
        self._events: set[str] = set()

    @property
    def domain(self) -> str:
        return "__publisher__" + uuid.uuid4().hex[:8]

    def set_defaults(self, defaults: dict):
        pass

    def register(self, event_topic: str):
        self._events.add(event_topic)

    def get_command_handler(self, command: IMessage) -> AnyCallable:
        raise NotImplementedError()

    def get_event_handlers(self, event: IMessage) -> t.Sequence[AnyCallable]:
        if event.__topic__ in self._events:
            return (partial(self._publisher, event),)
        return ()

    def get_subscriptions(self) -> set[str]:
        return set(self._events)
