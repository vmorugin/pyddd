import typing as t
from pyddd.application.abstractions import (
    IApplication,
    ApplicationSignal,
)
from pyddd.infrastructure.transport.core.abstractions import IMessageConsumer

from pyddd.infrastructure.transport.sync.domain.abstractions import (
    INotificationQueue,
    IAskPolicy,
    IEventFactory,
    INotification,
)


class MessageConsumer(IMessageConsumer):
    def __init__(
        self,
        queue: INotificationQueue,
        ask_policy: IAskPolicy,
        event_factory: IEventFactory,
    ):
        self._queue = queue
        self._ask_policy = ask_policy
        self._application: t.Optional[IApplication] = None
        self._subscriptions: set[str] = set()
        self._event_factory = event_factory

    @property
    def subscriptions(self):
        return self._subscriptions

    def subscribe(self, topic: str):
        self._subscriptions.add(topic)

    def set_application(self, application: IApplication):
        application.subscribe(ApplicationSignal.BEFORE_RUN, listener=self._before_run_handler)
        application.subscribe(ApplicationSignal.AFTER_RUN, listener=self._after_run_handler)
        application.subscribe(ApplicationSignal.BEFORE_STOP, listener=self._before_stop_handler)
        application.subscribe(ApplicationSignal.AFTER_STOP, listener=self._after_stop_handler)

        self._application = application

    def _before_run_handler(self, _signal: ApplicationSignal, _app: IApplication):
        for topic in self._subscriptions:
            self._queue.bind(topic)

    def _after_run_handler(self, _signal: ApplicationSignal, _app: IApplication):
        self._queue.consume(self._ask_message)

    def _before_stop_handler(self, _signal: ApplicationSignal, _app: IApplication):
        self._queue.stop_consume()

    def _after_stop_handler(self, _signal: ApplicationSignal, _app: IApplication): ...

    def _ask_message(self, message: INotification):
        if self._application:
            self._ask_policy.process(
                notification=message,
                event_factory=self._event_factory,
                application=self._application,
            )
