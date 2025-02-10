import logging
from collections import defaultdict

from application.condition import (
    none_condition,
)
from application.abstractions import (
    ICondition,
    IExecutor,
    IPayloadConverter,
)
from application.exceptions import FailedHandlerCondition
from application.executor import (
    SyncExecutor,
)
from application.handler import (
    EventHandler,
    CommandHandler,
)
from domain.message import IMessage


class Module:
    def __init__(
            self,
            domain: str,
            executor: IExecutor = None,
            logger_name: str = 'pyddd.module'
    ):
        self._domain = domain
        self._executor = executor or SyncExecutor()
        self._defaults = {}
        self._event_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._command_handlers: dict[str, CommandHandler] = {}
        self._logger = logging.getLogger(logger_name)

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
            condition: ICondition = none_condition,
    ):
        def wrapper(func):
            handler = EventHandler(CommandHandler(func))
            handler.set_converter(converter)
            handler.set_condition(condition)
            handler.set_defaults(self._defaults)
            self._event_handlers[event_name].append(handler)
            return func

        return wrapper

    def get_command_handler(self, command: IMessage):
        if command.topic not in self._command_handlers:
            raise RuntimeError(f'Unregistered command {command.topic} in {self.__class__.__name__}:{self._domain}')
        return self._command_handlers[command.topic].resolve(command)

    def get_event_handlers(self, event: IMessage):
        handlers = []
        for handler in self._event_handlers.get(event.topic, []):
            try:
                handlers.append(handler.resolve(event))
            except FailedHandlerCondition as exc:
                self._logger.debug(f"Handler {handler} with event {event} did not pass condition", exc_info=exc)
            except Exception as exc:
                self._logger.warning(f"Can not resolve message {event} with handler {handler}", exc_info=exc)
        return handlers
