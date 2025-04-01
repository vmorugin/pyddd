from unittest.mock import Mock
from pyddd.application.handler import (
    CommandHandler,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
)


class ExampleCommand(DomainCommand, domain='test'):
    ...


class ExampleEvent(DomainEvent, domain='test'):
    ...


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
        handler.resolve(ExampleEvent())()
        assert mock.called

    def test_with_default_override(self):
        def foo(cmd: ExampleCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=Mock()))
        func = handler.resolve(ExampleCommand())
        assert func(callback=mock) is mock
