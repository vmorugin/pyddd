import datetime as dt

import pytest

from pyddd.domain.message import (
    Message,
)
from pyddd.domain.abstractions import (
    MessageType,
    Version,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)


class TestMessage:
    def test_message(self):
        message = Message(
            full_name="users.sub.UserCreated",
            message_type=MessageType.EVENT,
            message_id="123",
            payload=dict(reference="123"),
        )
        assert message.__type__ == "EVENT"
        assert message.__message_name__ == "UserCreated"
        assert message.__domain__ == "users.sub"
        assert message.__version__ == 1
        assert message.to_dict() == {"reference": "123"}
        assert message.to_json() == '{"reference": "123"}'
        assert isinstance(message.__timestamp__, dt.datetime)

    def test_eq(self):
        message = Message(
            full_name="users.sub.UserCreated",
            message_type=MessageType.EVENT,
            message_id="123",
            payload=dict(reference="123"),
        )
        assert message == message


class ExampleEvent(DomainEvent, domain="test"):
    some_attr: str


class TestDomainEvent:
    def test_event(self):
        event = ExampleEvent(some_attr="123")

        assert event.__type__ == MessageType.EVENT
        assert event.to_dict() == {"some_attr": "123"}
        assert event.__domain__ == "test"
        assert event.__message_name__ == "ExampleEvent"
        assert event.__topic__ == "test.ExampleEvent"
        assert event.__version__ == 1

    def test_attrs_from_cls(self):
        assert ExampleEvent.__message_name__ == "ExampleEvent"
        assert ExampleEvent.__domain__ == "test"
        assert ExampleEvent.__topic__ == "test.ExampleEvent"

    def test_event_without_domain(self):
        with pytest.raises(ValueError):
            class ExampleEvent(DomainEvent): ...

    def test_could_create_with_version(self):
        class VersionedEvent(DomainEvent, domain="test", version=2):
            ...

        assert VersionedEvent.__version__ == Version(2)


class ExampleCommand(DomainCommand, domain="test"): ...


class TestDomainCommand:
    def test_command(self):
        command = ExampleCommand()
        assert command.__type__ == MessageType.COMMAND
        assert command.__domain__ == "test"
        assert command.__message_name__ == "ExampleCommand"
        assert command.__topic__ == "test.ExampleCommand"
        assert command.to_dict() == {}
        assert isinstance(command.__timestamp__, dt.datetime)
        assert isinstance(command.__message_id__, str)

    def test_attrs_from_cls(self):
        assert ExampleCommand.__message_name__ == "ExampleCommand"
        assert ExampleCommand.__domain__ == "test"
        assert ExampleCommand.__topic__ == "test.ExampleCommand"

    def test_command_without_domain(self):
        with pytest.raises(ValueError):
            class ExampleCommand(DomainCommand): ...

    def test_load_from_dict(self):
        class TestCommand(DomainCommand, domain="test"):
            reference: str

        command = TestCommand.load(payload={"reference": "123"})
        assert command.__type__ == "COMMAND"
        assert command.__message_name__ == "TestCommand"
        assert command.__domain__ == "test"
        assert command.to_dict() == {"reference": "123"}
        assert command.to_json() == '{"reference":"123"}'
        assert isinstance(command.__timestamp__, dt.datetime)
        assert isinstance(command.__message_id__, str)

    def test_could_create_with_version(self):
        class VersionedCommand(DomainCommand, domain="test", version=2):
            ...

        assert VersionedCommand.__version__ == Version(2)
