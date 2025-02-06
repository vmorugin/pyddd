from collections import defaultdict
from application.executor import (
    IExecutor,
    SyncExecutor,
)
from application.handler import (
    EventHandler,
    CommandHandler,
    IPayloadConverter,
)
from domain.message import IMessage


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

    def handle_command(self, command: IMessage, **kwargs):
        return self._executor.process_command(command, self._command_handlers[command.topic], **kwargs)

    def handle_event(self, event: IMessage, **kwargs):
        """
        todo: Handler executor
        """
        return self._executor.process_event(event, self._event_handlers[event.topic], **kwargs)

    def can_handle(self, message: IMessage) -> bool:
        return message.topic in self._event_handlers | self._command_handlers
