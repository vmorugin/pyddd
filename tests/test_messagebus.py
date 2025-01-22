import pytest

from application import Application
from application import (
    SyncExecutor,
)
from application import (
    EventHandler,
    CommandHandler,
)
from application import Module
from application.executor import IExecutor

from domain import (
    DomainCommand,
    DomainEvent,
)
from unittest.mock import Mock



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


class TestSyncExecutor:
    def test_init(self):
        executor = SyncExecutor()
        assert isinstance(executor, IExecutor)

    def test_process_command(self):
        def foo(cmd: TestCommand):
            return True

        executor = SyncExecutor()
        result = executor.process_command(command=TestCommand(), handler=CommandHandler(foo))
        assert result is True

    def test_process_event(self):
        def foo(cmd: TestCommand, callback):
            callback(True)

        executor = SyncExecutor()
        mock = Mock()
        executor.process_event(event=TestEvent(), handlers=[EventHandler(CommandHandler(foo))], callback=mock)
        mock.assert_called_with(True)


class TestModule:
    def test_register_as_decorator(self):
        module = Module('test')

        @module.register
        def foo(cmd: TestCommand):
            return True

        assert foo(cmd=TestCommand()) is True

    def test_subscribe_as_decorator(self):
        module = Module('test')

        @module.subscribe('test_event.Test')
        @module.register
        def foo(cmd: TestCommand):
            return True

        assert foo(cmd=TestCommand()) is True

    def test_domain(self):
        module = Module('test')
        assert module.domain == 'test'

    def test_register_without_command(self):
        def foo():
            ...

        module = Module('domain')
        with pytest.raises(AttributeError):
            module.register(foo)

    def test_subscribe_without_command_error(self):
        def foo():
            ...

        module = Module('domain')
        with pytest.raises(AttributeError):
            module.subscribe('domain.Test')(foo)

    def test_register_twice_error(self):
        def foo(cmd: TestCommand):
            ...

        module = Module('domain')
        module.register(foo)
        with pytest.raises(ValueError, match="Already registered command 'test.TestCommand'"):
            module.register(foo)

    def test_handle_command(self):
        module = Module(domain='test')

        @module.register
        def foo(cmd: TestCommand, bar: str):
            return bar

        module.set_defaults(dict(bar='bzz'))
        result = module.handle_command(TestCommand())
        assert result == 'bzz'

    def test_handle_events(self):
        class TestCommand2(DomainCommand, domain='test'):
            ...

        module = Module(domain='test')

        @module.subscribe(TestEvent.__topic__)
        @module.register
        def foo(command: TestCommand, callback):
            callback()

        @module.subscribe(TestEvent.__topic__)
        @module.register
        def bzz(command: TestCommand2, callback):
            callback()

        mock = Mock()
        module.set_defaults(dict(callback=mock))
        module.handle_event(TestEvent())
        assert mock.call_count == 2

    def test_handle_event_with_fail(self):
        def foo(command: TestCommand):
            assert False

        def bzz(command: TestCommand, callback):
            assert isinstance(command, TestCommand)
            callback()

        module = Module(domain='test')
        mock = Mock()
        module.set_defaults(dict(callback=mock))
        module.register(foo)
        module.subscribe(TestEvent.__topic__)(foo)
        module.subscribe(TestEvent.__topic__)(bzz)
        module.handle_event(TestEvent())
        assert mock.call_count == 1

    def test_subscribe_with_converter(self):
        class TestCommandWithParam(DomainCommand, domain='test'):
            reference: str

        class TestEventWithParam(DomainEvent, domain='test'):
            param_id: str

        def foo(command: TestCommandWithParam, callback):
            assert isinstance(command, TestCommandWithParam)
            callback(reference=command.reference)

        module = Module(domain='test')
        mock = Mock()
        module.set_defaults(dict(callback=mock))
        module.register(foo)
        module.subscribe(TestEventWithParam.__topic__, converter=lambda x: {'reference': x['param_id']})(foo)
        module.handle_event(TestEventWithParam(param_id='123'), callback=mock)
        mock.assert_called_with(reference='123')


class TestApplication:
    def test_include_twice(self):
        app = Application()
        app.include(Module('test'))
        with pytest.raises(ValueError, match="Already registered domain 'test'"):
            app.include(Module('test'))

    def test_handle_command(self):
        def foo(cmd: TestCommand):
            return True

        app = Application()
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(TestCommand())
        assert result is True

    def test_handle_event(self):
        def foo(cmd: TestCommand, callback):
            callback()

        app = Application()
        module = Module('test')
        module.subscribe(TestEvent.__topic__)(foo)
        app.include(module)
        mock = Mock()
        app.handle(TestEvent(), callback=mock)
        assert mock.called

    def test_handle_unresolved_event(self):
        app = Application()
        app.handle(TestEvent())

    def test_handle_unresolved_command(self):
        app = Application()
        with pytest.raises(ValueError, match='Unregistered module for domain'):
            app.handle(TestCommand())

    def test_handle_with_defaults(self):
        def foo(cmd: TestCommand, atr: str):
            return atr

        app = Application()
        app.set_defaults('test', atr='success')
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(TestCommand())
        assert result == 'success'
