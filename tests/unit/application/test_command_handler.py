from unittest.mock import Mock

import pytest

from pyddd.application.handler import (
    CommandHandler,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)
from pyddd.domain.types import FrozenJsonDict


class ExampleCommand(DomainCommand, domain="test.command-handler"): ...


class TestCommandHandler:
    def test_must_resolve(self):
        def foo(cmd: ExampleCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        func = handler.resolve(ExampleCommand())
        assert func(callback=mock) is mock

    def test_handler_must_store_command_type(self):
        def foo(cmd: ExampleCommand):
            return ...

        handler = CommandHandler(foo)
        assert handler.get_command_type() == ExampleCommand

    def test_handle_with_defaults_no_in_signature(self):
        def foo(cmd: ExampleCommand):
            return cmd

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=mock))
        command = ExampleCommand()
        func = handler.resolve(command)
        assert isinstance(func(), ExampleCommand)

    def test_with_defaults(self):
        def foo(cmd: ExampleCommand, callback):
            callback()

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=mock))
        handler.resolve(ExampleCommand())()
        assert mock.called

    def test_with_default_override(self):
        def foo(cmd: ExampleCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=Mock()))
        func = handler.resolve(ExampleCommand())
        assert func(callback=mock) is mock

    def test_could_resolve_frozen_dict_type(self):
        class TestCommand(DomainCommand, domain="test"):
            foo: FrozenJsonDict

            class Config:
                arbitrary_types_allowed = True

        def foo(command: TestCommand):
            return command.foo["success"]

        handler = CommandHandler(foo)
        func = handler.resolve(TestCommand(foo=FrozenJsonDict({"success": True})))
        result = func()
        assert result is True

    def test_could_not_register_with_event(self):
        class TestEvent(DomainEvent, domain="test"): ...

        def foo(command: TestEvent):
            return command.foo["success"]

        with pytest.raises(AttributeError):
            CommandHandler(foo)
