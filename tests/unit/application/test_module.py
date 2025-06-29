import uuid
from unittest.mock import Mock

import pytest

from pyddd.application import (
    Module,
    SyncExecutor,
)
from pyddd.application.abstractions import (
    ICondition,
    IRetryStrategy,
    AnyCallable,
    IModule,
)
from pyddd.domain import (
    DomainCommand,
    DomainEvent,
    DomainName,
)
from pyddd.domain.abstractions import IEvent
from pyddd.domain.types import FrozenJsonDict

__domain__ = DomainName("test.module")


class ExampleCommand(DomainCommand, domain=__domain__): ...


class ExampleEvent(DomainEvent, domain=__domain__): ...


class TestModule:
    def test_must_implement_interface(self):
        module = Module("test")
        assert isinstance(module, IModule)

    @pytest.mark.parametrize("domain", (None, "", "..test.", "_@?domain"))
    def test_must_raise_error_if_incorrect_domain(self, domain):
        with pytest.raises(ValueError):
            Module(domain)

    def test_register_as_decorator(self):
        module = Module("test")

        @module.register
        def foo(cmd: ExampleCommand):
            return True

        assert foo(cmd=ExampleCommand()) is True

    def test_subscribe_as_decorator(self):
        module = Module("test")

        @module.subscribe("test_event.Test")
        @module.register
        def foo(cmd: ExampleCommand):
            return True

        assert foo(cmd=ExampleCommand()) is True

    def test_domain(self):
        module = Module("test")
        assert module.domain == "test"

    def test_register_without_command(self):
        def foo(): ...

        module = Module("domain")
        with pytest.raises(AttributeError):
            module.register(foo)

    def test_subscribe_without_command_error(self):
        def foo(): ...

        module = Module("domain")
        with pytest.raises(AttributeError):
            module.subscribe("domain.Test")(foo)

    def test_register_twice_error(self):
        def foo(cmd: ExampleCommand): ...

        module = Module("domain")
        module.register(foo)
        with pytest.raises(ValueError, match="Already registered command 'test.module.ExampleCommand'"):
            module.register(foo)

    def test_handler_unregistered_command_must_fail(self):
        module = Module("domain")
        with pytest.raises(
            RuntimeError,
            match="Unregistered command test.module.ExampleCommand in Module:domain",
        ):
            module.get_command_handler(ExampleCommand())

    def test_handle_command(self):
        module = Module(domain="test")

        @module.register
        def foo(cmd: ExampleCommand, bar: str):
            return bar

        module.set_defaults(dict(bar="bzz"))
        handler = module.get_command_handler(ExampleCommand())
        assert handler() == "bzz"

    def test_handle_events(self):
        class ExampleCommand2(DomainCommand, domain=__domain__): ...

        module = Module(domain=__domain__)

        @module.subscribe(ExampleEvent.__topic__)
        @module.register
        def foo(command: ExampleCommand, callback):
            callback()

        @module.subscribe(ExampleEvent.__topic__)
        @module.register
        def bzz(command: ExampleCommand2, callback):
            callback()

        mock = Mock()
        module.set_defaults(dict(callback=mock))
        event = ExampleEvent()
        handlers = module.get_event_handlers(event)
        [handler() for handler in handlers]
        assert mock.call_count == 2

    def test_could_subscribe_with_two_events_to_one_command(self):
        class ExampleEvent1(DomainEvent, domain=__domain__): ...

        class ExampleEvent2(DomainEvent, domain=__domain__): ...

        module = Module(domain=__domain__)

        @module.subscribe(ExampleEvent1.__topic__)
        @module.subscribe(ExampleEvent2.__topic__)
        @module.register
        def bzz(command: ExampleCommand):
            return 1

        event_1 = ExampleEvent1()
        handlers = module.get_event_handlers(event_1)
        assert len(handlers) == 1
        assert handlers[0]() == 1

        event_2 = ExampleEvent2()
        handlers = module.get_event_handlers(event_2)
        assert len(handlers) == 1
        assert handlers[0]() == 1

    def test_must_return_results_when_handle_events(self):
        class ExampleCommand3(DomainCommand, domain=__domain__): ...

        module = Module(domain=__domain__, executor=SyncExecutor())

        @module.subscribe(ExampleEvent.__topic__)
        @module.register
        def foo(command: ExampleCommand):
            return 1

        @module.subscribe(ExampleEvent.__topic__)
        @module.register
        def bzz(command: ExampleCommand3, callback):
            return 2

        mock = Mock()
        module.set_defaults(dict(callback=mock))
        handlers = module.get_event_handlers(ExampleEvent())

        assert [h() for h in handlers] == [1, 2]

    def test_can_subscribe_with_converter(self):
        class ExampleCommandWithParam(DomainCommand, domain=__domain__):
            reference: str

        class ExampleEventWithParam(DomainEvent, domain=__domain__):
            param_id: str

        def foo(command: ExampleCommandWithParam, callback):
            assert isinstance(command, ExampleCommandWithParam)
            callback(reference=command.reference)

        module = Module(domain=__domain__)
        mock = Mock()
        module.set_defaults(dict(callback=mock))
        module.register(foo)
        event = ExampleEventWithParam(param_id="123")
        module.subscribe(event.__topic__, converter=lambda x: {"reference": x["param_id"]})(foo)
        handlers = module.get_event_handlers(event)
        assert len(handlers) == 1
        handlers[0](callback=mock)
        mock.assert_called_with(reference="123")

    def test_can_subscribe_with_different_converters(self):
        class ExampleCommandWithReferenceParam(DomainCommand, domain=__domain__):
            reference: str

        class ExampleEventWithFooParam(DomainEvent, domain=__domain__):
            foo: str

        class ExampleEventWithBarParam(DomainEvent, domain=__domain__):
            bar: str

        module = Module(domain=__domain__)

        @module.subscribe(
            ExampleEventWithFooParam.__topic__,
            converter=lambda x: {"reference": x["foo"]},
        )
        @module.subscribe(
            ExampleEventWithBarParam.__topic__,
            converter=lambda x: {"reference": x["bar"]},
        )
        @module.register
        def foo(command: ExampleCommandWithReferenceParam, callback):
            assert isinstance(command, ExampleCommandWithReferenceParam)
            callback(reference=command.reference)

        mock = Mock()
        foo_event = ExampleEventWithFooParam(foo=str(uuid.uuid4()))
        handlers = module.get_event_handlers(foo_event)
        assert len(handlers) == 1
        handlers[0](callback=mock)
        mock.assert_called_with(reference=foo_event.foo)

        bar_event = ExampleEventWithBarParam(bar=str(uuid.uuid4()))
        handlers = module.get_event_handlers(bar_event)
        assert len(handlers) == 1
        handlers[0](callback=mock)
        mock.assert_called_with(reference=bar_event.bar)

    def test_must_fail_when_get_command_handler_not_existed(self):
        module = Module("test")
        with pytest.raises(RuntimeError):
            module.get_command_handler(ExampleCommand())

    def test_must_fail_when_get_command_handler_but_got_event(self):
        module = Module("test")

        @module.subscribe(ExampleEvent.__topic__)
        @module.register
        def foo(command: ExampleCommand):
            return True

        with pytest.raises(RuntimeError):
            module.get_command_handler(ExampleEvent())

    def test_must_return_empty_list_when_get_unregistered_event_handlers(self):
        module = Module("test")
        handlers = module.get_event_handlers(ExampleEvent())
        assert handlers == []

    def test_must_returns_list_event_handlers_when_registered(self):
        module = Module("test")

        @module.subscribe(ExampleEvent.__topic__)
        @module.register
        def foo(command: ExampleCommand):
            return True

        handlers = module.get_event_handlers(ExampleEvent())
        assert len(handlers) == 1
        assert handlers[0]() is True

    def test_could_handle_with_frozen_dict_type(self):
        module = Module(__domain__)

        class TestCommand(DomainCommand, domain=__domain__):
            foo: FrozenJsonDict

            class Config:
                arbitrary_types_allowed = True

        @module.register
        def foo(command: TestCommand):
            return command.foo["result"]

        handler = module.get_command_handler(TestCommand(foo=FrozenJsonDict({"result": True})))
        assert handler() is True

    def test_must_not_return_handler_if_fail_condition(self):
        class FailCondition(ICondition):
            def check(self, event: IEvent) -> bool:
                return False

        module = Module("test")
        condition = FailCondition()

        @module.subscribe(ExampleEvent.__topic__, condition=condition)
        @module.register
        def foo(command: ExampleCommand):
            return True

        handlers = module.get_event_handlers(ExampleEvent())
        assert len(handlers) == 0

    def test_can_handle_with_retry_strategy(self):
        class RetryStrategy(IRetryStrategy):
            def __init__(self, retry_count: int):
                self._count = retry_count

            def __call__(self, func: AnyCallable) -> AnyCallable:
                count = self._count

                def wrapper(*args, **kwargs):
                    nonlocal count
                    while count > 0:
                        try:
                            return func(*args, **kwargs)
                        except Exception:
                            count -= 1
                    return func(*args, **kwargs)

                return wrapper

        module = Module("test")

        @module.subscribe(ExampleEvent.__topic__, retry_strategy=RetryStrategy(retry_count=3))
        @module.register
        def foo(command: ExampleCommand, callback):
            return callback()

        mock = Mock(side_effect=[Exception(), Exception(), 1])
        handlers = module.get_event_handlers(ExampleEvent())
        assert len(handlers) == 1
        assert handlers[0](callback=mock) == 1
        assert mock.call_count == 3
