from unittest.mock import (
    Mock,
    AsyncMock,
)

from pyddd.application import Application
from pyddd.application.signal_manager import (
    SignalManager,
)
from pyddd.application.abstractions import (
    ApplicationSignal,
    SignalListener,
    ISignalManager,
)


class TestApplicationSignalManager:
    def test_must_impl_interface(self):
        manager = SignalManager()
        assert isinstance(manager, ISignalManager)

    def test_can_subscribe_to_event_and_notify(self):
        manager = SignalManager()
        mock = Mock(spec=SignalListener)
        application = Application()
        manager.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        manager.notify(ApplicationSignal.BEFORE_RUN, application)
        mock.assert_called_with(ApplicationSignal.BEFORE_RUN, application)

    async def test_can_subscribe_to_event_and_notify_async(self):
        manager = SignalManager()
        mock = AsyncMock(spec=SignalListener)
        application = Application()
        manager.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        await manager.notify_async(ApplicationSignal.BEFORE_RUN, application)
        mock.assert_called_with(ApplicationSignal.BEFORE_RUN, application)

    def test_can_unsubscribe_to_event(self):
        manager = SignalManager()
        mock = Mock(spec=SignalListener)
        application = Application()
        manager.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        manager.unsubscribe(ApplicationSignal.BEFORE_RUN, mock)
        manager.notify(ApplicationSignal.BEFORE_RUN, application)
        mock.assert_not_called()

    def test_must_not_notify_different_event(self):
        manager = SignalManager()
        mock = Mock(spec=SignalListener)
        application = Application()
        manager.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        manager.notify(ApplicationSignal.AFTER_RUN, application)
        mock.assert_not_called()

    async def test_must_not_notify_async_different_event(self):
        manager = SignalManager()
        mock = Mock(spec=SignalListener)
        application = Application()
        manager.subscribe(ApplicationSignal.BEFORE_RUN, mock)
        await manager.notify_async(ApplicationSignal.AFTER_RUN, application)
        mock.assert_not_called()