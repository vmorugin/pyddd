from unittest.mock import Mock

from pyddd.application.abstractions import (
    IModule,
)
from pyddd.domain import DomainEvent
from pyddd.infrastructure.transport.core.publisher import EventPublisherModule


class FakeEvent(DomainEvent, domain='test.event'):
    ...


class TestEventPublisher:
    def test_must_implement_interface(self):
        module = EventPublisherModule(publisher=Mock())
        assert isinstance(module, IModule)
        assert module.domain.startswith('__publisher__')

    def test_must_have_different_domains_postfix(self):
        publisher = Mock()
        assert EventPublisherModule(publisher).domain != EventPublisherModule(publisher).domain

    def test_can_register_messages(self):
        module = EventPublisherModule(Mock())
        module.register('test.event.TestDomainEvent')
        module.register('test.event.AnotherDomainEvent')
        assert module.get_subscriptions() == {'test.event.TestDomainEvent', 'test.event.AnotherDomainEvent'}

    def test_get_event_handlers_not_registered_must_be_empty(self):
        module = EventPublisherModule(Mock())
        assert module.get_event_handlers(FakeEvent()) == ()

    def test_get_event_handlers_must_call_publisher_when_registered(self):
        callback = Mock()
        event = FakeEvent()
        module = EventPublisherModule(callback)
        module.register(event.__topic__)
        funcs = module.get_event_handlers(event)
        assert len(funcs) == 1
        funcs[0]()
        callback.assert_called_with(event)
