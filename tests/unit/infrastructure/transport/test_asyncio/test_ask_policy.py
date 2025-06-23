from unittest.mock import (
    Mock,
    AsyncMock,
)

import pytest

from pyddd.application import Application
from pyddd.domain import DomainEvent

from pyddd.infrastructure.transport.asyncio.domain import (
    DefaultAskPolicy,
    IAskPolicy,
)
from pyddd.infrastructure.transport.core.abstractions import (
    IPublishedMessage,
    IEventFactory,
)


class TestDefaultAskPolicy:
    @pytest.fixture
    def policy(self):
        return DefaultAskPolicy()

    @pytest.fixture
    def notification(self):
        notification = Mock(spec=IPublishedMessage)
        notification.reject = AsyncMock()
        return notification

    @pytest.fixture
    def app(self):
        app = AsyncMock(spec=Application)
        app.handle = AsyncMock(return_value=[True])
        return app

    @pytest.fixture
    def domain_event(self):
        return Mock(spec=DomainEvent)

    @pytest.fixture
    def event_factory(self, domain_event):
        event_factory = Mock(spec=IEventFactory)
        event_factory.build_event.return_value = domain_event
        return event_factory

    def test_must_implement_interface(self, policy):
        assert isinstance(policy, IAskPolicy)

    async def test_must_call_app_handle(self, policy, notification, app, event_factory, domain_event):
        await policy.process(notification, event_factory=event_factory, application=app)
        app.handle.assert_called_with(domain_event)

    async def test_must_ack_if_success(self, policy, notification, app, event_factory):
        await policy.process(notification, event_factory=event_factory, application=app)
        assert notification.ack.called

    async def test_must_not_ask_if_error_build_message(self, policy, notification, app, event_factory):
        event_factory.build_event.side_effect = Exception()
        await policy.process(notification, event_factory=event_factory, application=app)
        assert not notification.ack.called

    async def test_must_not_ask_if_handling_message(self, policy, notification, app, event_factory):
        app.handle.side_effect = Exception()
        await policy.process(notification, event_factory=event_factory, application=app)
        assert not notification.ack.called
