import datetime as dt

import pytest

from pyddd.domain.message import (
    Message,
    MessageType,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)


class TestMessage:
    def test_message(self):
        message = Message(
            full_name='users.sub.UserCreated',
            message_type=MessageType.EVENT,
            message_id='123',
            payload=dict(reference='123'),
        )
        assert message.type == 'EVENT'
        assert message.message_name == 'UserCreated'
        assert message.domain == 'users.sub'
        assert message.to_dict() == {'reference': '123'}
        assert message.to_json() == '{"reference": "123"}'
        assert isinstance(message.occurred_on, dt.datetime)

class TestDomainEvent:
    def test_event(self):
        class ExampleEvent(DomainEvent, domain='test'):
            some_attr: str

        event = ExampleEvent(some_attr='123')

        assert event.type == MessageType.EVENT
        assert event.to_dict() == {'some_attr': '123'}
        assert event.domain == 'test'
        assert event.message_name == 'ExampleEvent'
        assert event.topic == 'test.ExampleEvent'

    def test_attrs_from_cls(self):
        class ExampleEvent(DomainEvent, domain='test'):
            some_attr: str

        assert ExampleEvent.__message_name__ == 'ExampleEvent'
        assert ExampleEvent.__domain__ == 'test'
        assert ExampleEvent.__topic__ == 'test.ExampleEvent'

    def test_event_without_domain(self):
        with pytest.raises(ValueError):
            class TestEvent(DomainEvent):
                ...

class TestDomainCommand:
    def test_command(self):
        class ExampleCommand(DomainCommand, domain='test'):
            ...

        command = ExampleCommand()
        assert command.type == MessageType.COMMAND
        assert command.domain == 'test'
        assert command.message_name == 'ExampleCommand'
        assert command.topic == 'test.ExampleCommand'
        assert command.to_dict() == {}
        assert isinstance(command.occurred_on, dt.datetime)
        assert isinstance(command.message_id, str)

    def test_attrs_from_cls(self):
        class ExampleCommand(DomainCommand, domain='test'):
            some_attr: str

        assert ExampleCommand.__message_name__ == 'ExampleCommand'
        assert ExampleCommand.__domain__ == 'test'
        assert ExampleCommand.__topic__ == 'test.ExampleCommand'

    def test_command_without_domain(self):
        with pytest.raises(ValueError):
            class ExampleCommand(DomainCommand):
                ...