from collections import defaultdict

from application.executor import (
    IExecutor,
    SyncExecutor,
)
from application.handler import (
    EventHandler,
    CommandHandler,
    IPayloadConverter,
    IHandler,
)


class Module:
    def __init__(self, domain: str, executor: IExecutor = None):
        self._domain = domain
        self._executor = executor or SyncExecutor()
        self._defaults = {}
        self._event_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._command_handlers: dict[str, CommandHandler] = {}

    @property
    def domain(self) -> str:
        return self._domain

    def set_defaults(self, defaults: dict):
        self._defaults.update(defaults)

    def register(self, func):
        handler = CommandHandler(func)
        command_type = handler.get_command_type()
        handler.set_defaults(self._defaults)
        if command_type.__topic__ in self._command_handlers:
            raise ValueError(f"Already registered command '{command_type.__topic__}'")
        self._command_handlers[command_type.__topic__] = handler
        return func

    def subscribe(
            self,
            event_name: str,
            *,
            converter: IPayloadConverter = lambda x: x,
    ):
        def wrapper(func):
            handler = EventHandler(CommandHandler(func))
            handler.set_converter(converter)
            handler.set_defaults(self._defaults)
            self._event_handlers[event_name].append(handler)
            return func

        return wrapper

    def get_command_handler(self, topic: str) -> IHandler:
        if topic not in self._command_handlers:
            raise RuntimeError(f'Unregistered command {topic} in {self.__class__.__name__}:{self._domain}')
        return self._command_handlers[topic]

    def get_event_handlers(self, topic: str) -> list[IHandler]:
        handlers = []
        for handler in self._event_handlers.get(topic, []):
            handlers.append(handler)
        return handlers
