from unittest.mock import Mock

import pytest

from application import Module
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
