import datetime as dt

import pytest

from pyddd.domain import (
    DomainCommand,
    DomainName,
)
from pyddd.domain.abstractions import (
    MessageType,
    Version,
)

__domain__ = DomainName("test.command")


class ExampleCommand(DomainCommand, domain=__domain__): ...


class TestDomainCommand:
    def test_command(self):
        command = ExampleCommand()
        assert command.__type__ == MessageType.COMMAND
        assert command.__domain__ == "test.command"
        assert command.__message_name__ == "ExampleCommand"
        assert command.__topic__ == "test.command.ExampleCommand"
        assert command.to_dict() == {}
        assert isinstance(command.__timestamp__, dt.datetime)
        assert isinstance(command.__message_id__, str)

    def test_attrs_from_cls(self):
        assert ExampleCommand.__message_name__ == "ExampleCommand"
        assert ExampleCommand.__domain__ == "test.command"
        assert ExampleCommand.__topic__ == "test.command.ExampleCommand"

    def test_command_without_domain(self):
        with pytest.raises(ValueError):

            class ExampleCommand(DomainCommand): ...

    def test_load_from_dict(self):
        class TestCommand(DomainCommand, domain=__domain__):
            reference: str

        command = TestCommand.load(payload={"reference": "123"})
        assert command.__type__ == "COMMAND"
        assert command.__message_name__ == "TestCommand"
        assert command.__domain__ == "test.command"
        assert command.to_dict() == {"reference": "123"}
        assert command.to_json() == '{"reference":"123"}'
        assert isinstance(command.__timestamp__, dt.datetime)
        assert isinstance(command.__message_id__, str)

    def test_could_create_with_version(self):
        class VersionedCommand(DomainCommand, domain=__domain__, version=2): ...

        assert VersionedCommand.__version__ == Version(2)
