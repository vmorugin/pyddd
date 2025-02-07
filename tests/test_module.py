from unittest.mock import Mock

import pytest

from application import (
    Module,
    SyncExecutor,
)
from domain import (
    DomainCommand,
    DomainEvent,
)


class TestCommand(DomainCommand, domain='test'):
    ...


class TestEvent(DomainEvent, domain='test'):
    ...


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

    def test_handler_unregistered_command_must_fail(self):
        module = Module('domain')
        with pytest.raises(RuntimeError, match='Unregistered command test.TestCommand in Module:domain'):
            module.get_command_handler(TestCommand.__topic__)

    def test_handle_command(self):
        module = Module(domain='test')

        @module.register
        def foo(cmd: TestCommand, bar: str):
            return bar

        module.set_defaults(dict(bar='bzz'))
        handler = module.get_command_handler(TestCommand.__topic__)
        assert handler.handle(TestCommand()) == 'bzz'

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
        handlers = module.get_event_handlers(TestEvent.__topic__)
        [handler.handle(TestEvent()) for handler in handlers]
        assert mock.call_count == 2

    def test_could_subscribe_with_two_events_to_one_command(self):
        class TestEvent1(DomainEvent, domain='test'):
            ...

        class TestEvent2(DomainEvent, domain='test'):
            ...

        module = Module(domain='test')

        @module.subscribe(TestEvent1.__topic__)
        @module.subscribe(TestEvent2.__topic__)
        @module.register
        def bzz(command: TestCommand):
            return 1

        handlers = module.get_event_handlers(TestEvent1.__topic__)
        assert len(handlers) == 1
        assert handlers[0].handle(TestEvent1()) == 1

        handlers = module.get_event_handlers(TestEvent2.__topic__)
        assert len(handlers) == 1
        assert handlers[0].handle(TestEvent2()) == 1

    def test_must_return_results_when_handle_events(self):
        class TestCommand2(DomainCommand, domain='test'):
            ...

        module = Module(domain='test', executor=SyncExecutor())

        @module.subscribe(TestEvent.__topic__)
        @module.register
        def foo(command: TestCommand):
            return 1

        @module.subscribe(TestEvent.__topic__)
        @module.register
        def bzz(command: TestCommand2, callback):
            return 2

        mock = Mock()
        module.set_defaults(dict(callback=mock))
        handlers = module.get_event_handlers(TestEvent.__topic__)

        assert [h.handle(TestEvent()) for h in handlers] == [1, 2]

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
        handlers = module.get_event_handlers(TestEventWithParam.__topic__)
        assert len(handlers) == 1
        handlers[0].handle(TestEventWithParam(param_id='123'), callback=mock)
        mock.assert_called_with(reference='123')

    def test_must_fail_when_get_command_handler_not_existed(self):
        module = Module('...')
        with pytest.raises(RuntimeError):
            module.get_command_handler(TestCommand.__topic__)

    def test_must_fail_when_get_command_handler_but_got_event(self):
        module = Module('...')

        @module.subscribe(TestEvent.__topic__)
        @module.register
        def foo(command: TestCommand):
            return True

        with pytest.raises(RuntimeError):
            module.get_command_handler(TestEvent.__topic__)

    def test_must_return_empty_list_when_get_unregistered_event_handlers(self):
        module = Module('...')
        handlers = module.get_event_handlers(TestEvent.__topic__)
        assert handlers == []

    def test_must_returns_list_event_handlers_when_registered(self):
        module = Module('...')

        @module.subscribe(TestEvent.__topic__)
        @module.register
        def foo(command: TestCommand):
            return True

        handlers = module.get_event_handlers(TestEvent.__topic__)
        assert len(handlers) == 1
        assert handlers[0].handle(TestEvent()) == True
