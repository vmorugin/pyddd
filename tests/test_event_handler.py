from functools import partial
from unittest.mock import Mock

import pytest

from pyddd.application.exceptions import FailedHandlerCondition
from pyddd.application.handler import (
    EventHandler,
)
from pyddd.application.abstractions import (
    ICondition,
    ICommandHandler,
    ResolvedHandlerT,
    IRetryStrategy,
)
from pyddd.domain import (
    DomainEvent,
    DomainCommand,
)
from pyddd.domain.event import IEvent
from pyddd.domain.message import IMessage


class ExampleEvent(DomainEvent, domain='test'):
    ...


class ExampleCommand(DomainCommand, domain='test'):
    ...


class FakeCommandHandler(ICommandHandler):
    def __init__(self, command_type, callback):
        self._command_type: type[DomainCommand] = command_type
        self._callback = callback
        self._defaults = {}

    def get_command_type(self) -> type[DomainCommand]:
        return self._command_type

    def resolve(self, message: IMessage, **kwargs) -> ResolvedHandlerT:
        return partial(self.handle, message, **kwargs)

    def handle(self, message: IMessage, **kwargs):
        return self._callback(message, **self._defaults | kwargs)

    def set_defaults(self, defaults: dict):
        self._defaults = defaults


class TestEventHandler:
    def test_handle(self):
        mock = Mock()
        handler = EventHandler(FakeCommandHandler(ExampleCommand, mock))
        handler.resolve(ExampleEvent())(callback=mock)
        assert mock.called

    def test_with_defaults(self):
        mock = Mock()
        handler = EventHandler(FakeCommandHandler(ExampleCommand, mock))
        handler.set_defaults(dict(callback=mock))
        handler.resolve(ExampleEvent())()
        assert mock.called

    def test_with_default_override(self):
        mock = Mock()
        handler = EventHandler(FakeCommandHandler(ExampleCommand, mock))
        handler.set_defaults(dict(callback=Mock()))
        handler.resolve(ExampleEvent())(callback=mock)
        assert mock.called

    def test_must_returns_result(self):
        class CustomEvent(DomainEvent, domain='test'):
            id: int

        class CustomCommand(DomainCommand, domain='test'):
            id: str

        callback = Mock(return_value='12')
        handler = EventHandler(FakeCommandHandler(CustomCommand, callback=callback))
        func = handler.resolve(CustomEvent(id=12))
        assert func() == '12'

    def test_must_resolve_event(self):
        callback = Mock(return_value='123')
        handler = EventHandler(FakeCommandHandler(ExampleCommand, callback))
        func = handler.resolve(ExampleEvent())
        assert func() == '123'

    def test_must_resolve_with_converter(self):
        class CustomCommand(DomainCommand, domain='test'):
            reference: str

        class CustomEvent(DomainEvent, domain='test'):
            id: str

        mock = Mock()
        handler = EventHandler(FakeCommandHandler(CustomCommand, mock))
        handler.set_converter(lambda x: {'reference': x['id']})
        func = handler.resolve(CustomEvent(id='123'))
        func(callback=mock)
        mock.assert_called_with(CustomCommand(reference='123'), callback=mock)

    def test_must_fail_resolve_when_fail_condition(self):
        class FailCondition(ICondition):
            def check(self, event: IEvent) -> bool:
                return False

        mock = Mock()
        handler = EventHandler(FakeCommandHandler(ExampleCommand, mock))
        handler.set_condition(FailCondition())
        with pytest.raises(FailedHandlerCondition, match='Failed check condition FailCondition'):
            handler.resolve(ExampleEvent())

    def test_always_call_retry_strategy(self):
        mock = Mock()
        retry_mock = Mock(spec=IRetryStrategy)
        handler = EventHandler(FakeCommandHandler(ExampleCommand, mock))
        handler.set_retry_strategy(retry_mock)
        handler.resolve(ExampleEvent())
        assert retry_mock.called
