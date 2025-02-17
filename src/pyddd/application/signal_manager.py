from collections import defaultdict
from contextlib import suppress

from pyddd.application.abstractions import (
    IApplication,
    ApplicationSignal,
    SignalListener,
    ISignalManager,
)


class SignalManager(ISignalManager):
    def __init__(self):
        self._listeners: dict[ApplicationSignal, set[SignalListener]] = defaultdict(set)

    def subscribe(self, signal: ApplicationSignal, listener: SignalListener):
        self._listeners[signal].add(listener)

    def unsubscribe(self, signal: ApplicationSignal, listener: SignalListener):
        with suppress(KeyError):
            self._listeners.get(signal, set()).remove(listener)

    def notify(self, signal: ApplicationSignal, application: IApplication):
        for listener in self._listeners.get(signal, []):
            listener(signal, application)

    async def notify_async(self, signal: ApplicationSignal, application: IApplication):
        for listener in self._listeners.get(signal, []):
            await listener(signal, application)
