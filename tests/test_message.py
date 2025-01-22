import datetime as dt

import pytest

from domain.message import (
    Message,
    MessageType,
)
from domain import (
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
        class TestEvent(DomainEvent, domain='test'):
            some_attr: str

        event = TestEvent(some_attr='123')

        assert event.type == MessageType.EVENT
        assert event.to_dict() == {'some_attr': '123'}
        assert event.domain == 'test'
        assert event.message_name == 'TestEvent'
        assert event.topic == 'test.TestEvent'

    def test_attrs_from_cls(self):
        class TestEvent(DomainEvent, domain='test'):
            some_attr: str

        assert TestEvent.__message_name__ == 'TestEvent'
        assert TestEvent.__domain__ == 'test'
        assert TestEvent.__topic__ == 'test.TestEvent'

    def test_event_without_domain(self):
        with pytest.raises(ValueError):
            class TestEvent(DomainEvent):
                ...

class TestDomainCommand:
    def test_command(self):
        class TestCommand(DomainCommand, domain='test'):
            ...

        command = TestCommand()
        assert command.type == MessageType.COMMAND
        assert command.domain == 'test'
        assert command.message_name == 'TestCommand'
        assert command.topic == 'test.TestCommand'
        assert command.to_dict() == {}
        assert isinstance(command.occurred_on, dt.datetime)
        assert isinstance(command.message_id, str)

    def test_attrs_from_cls(self):
        class TestCommand(DomainCommand, domain='test'):
            some_attr: str

        assert TestCommand.__message_name__ == 'TestCommand'
        assert TestCommand.__domain__ == 'test'
        assert TestCommand.__topic__ == 'test.TestCommand'

    def test_command_without_domain(self):
        with pytest.raises(ValueError):
            class TestCommand(DomainCommand):
                ...