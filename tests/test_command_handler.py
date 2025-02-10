from unittest.mock import Mock
from application import (
    CommandHandler,
)
from domain import (
    DomainCommand,
    DomainEvent,
)

class TestCommand(DomainCommand, domain='test'):
    ...

class TestEvent(DomainEvent, domain='test'):
    ...


class TestCommandHandler:
    def test_must_resolve(self):
        def foo(cmd: TestCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        func = handler.resolve(TestCommand())
        assert func(callback=mock) is mock


    def test_handler_must_store_command_type(self):
        def foo(cmd: TestCommand):
            return ...

        handler = CommandHandler(foo)
        assert handler.get_command_type() == TestCommand

    def test_handle_with_defaults_no_in_signature(self):
        def foo(cmd: TestCommand):
            return cmd

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=mock))
        command = TestCommand()
        func = handler.resolve(command)
        assert func() == command

    def test_with_defaults(self):
        def foo(cmd: TestCommand, callback):
            callback()

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=mock))
        handler.resolve(TestEvent())()
        assert mock.called

    def test_with_default_override(self):
        def foo(cmd: TestCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=Mock()))
        func = handler.resolve(TestCommand())
        assert func(callback=mock) is mock
