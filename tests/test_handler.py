from unittest.mock import Mock
from application import (
    EventHandler,
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


class TestEventHandler:
    def test_handle(self):
        def foo(cmd: TestCommand, callback):
            callback()

        mock = Mock()
        handler = EventHandler(CommandHandler(foo))
        handler.handle(TestEvent(), callback=mock)
        assert mock.called

    def test_with_defaults(self):
        def foo(cmd: TestCommand, callback):
            callback()

        mock = Mock()
        handler = EventHandler(CommandHandler(foo))
        handler.set_defaults(dict(callback=mock))
        handler.handle(TestEvent())
        assert mock.called

    def test_with_default_override(self):
        def foo(cmd: TestCommand, callback):
            callback()

        mock = Mock()
        handler = EventHandler(CommandHandler(foo))
        handler.set_defaults(dict(callback=Mock()))
        handler.handle(TestEvent(), callback=mock)
        assert mock.called

    def test_handle_with_converter(self):
        class CustomCommand(DomainCommand, domain='test'):
            reference: str

        class CustomEvent(DomainEvent, domain='test'):
            id: str

        def foo(cmd: CustomCommand, callback):
            callback(reference=cmd.reference)

        mock = Mock()
        handler = EventHandler(CommandHandler(foo))
        handler.set_converter(lambda x: {'reference': x['id']})
        handler.handle(CustomEvent(id='123'), callback=mock)
        mock.assert_called_with(reference='123')


class TestCommandHandler:
    def test_handle(self):
        def foo(cmd: TestCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        result = handler.handle(TestCommand(), callback=mock)
        assert result is mock
        assert handler.get_command_type() == TestCommand

    def test_handle_with_defaults_no_in_signature(self):
        def foo(cmd: TestCommand):
            return cmd

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=mock))
        command = TestCommand()
        result = handler.handle(command)
        assert result == command

    def test_with_defaults(self):
        def foo(cmd: TestCommand, callback):
            callback()

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=mock))
        handler.handle(TestEvent())
        assert mock.called

    def test_with_default_override(self):
        def foo(cmd: TestCommand, callback):
            return callback

        mock = Mock()
        handler = CommandHandler(foo)
        handler.set_defaults(dict(callback=Mock()))
        result = handler.handle(TestCommand(), callback=mock)
        assert result is mock
