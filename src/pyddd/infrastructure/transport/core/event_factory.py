from pyddd.domain.message import (
    Message,
    MessageType,
)

from pyddd.infrastructure.transport.core.abstractions import (
    IEventFactory,
    INotification,
)


class DomainEventFactory(IEventFactory):
    def build_event(self, message: INotification) -> Message:
        return Message(
            full_name=f"{message.name.replace(':', '.')}",
            message_type=MessageType.EVENT,
            payload=message.payload,
        )
