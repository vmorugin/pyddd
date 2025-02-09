import logging
from collections import defaultdict

from application.executor import SyncExecutor
from application.abstractions import IExecutor
from application.module import Module
from domain.message import (
    IMessage,
    MessageType,
)


class Application:
    def __init__(
            self,
            logger_name: str = 'pyddd.application',
            executor: IExecutor = None,
    ):
        self._modules: dict[str, Module] = {}
        self._defaults: dict[str, dict] = defaultdict(dict)
        self._logger = logging.getLogger(logger_name)
        self._executor = executor or SyncExecutor()

    def set_defaults(self, domain: str, **kwargs):
        self._defaults[domain].update(kwargs)
        if module := self._modules.get(domain):
            module.set_defaults(kwargs)

    def include(self, module: Module):
        if module.domain in self._modules:
            raise ValueError("Already registered domain 'test'")

        module.set_defaults(self._defaults[module.domain])
        self._modules[module.domain] = module

    def handle(self, message: IMessage, **depends):
        if not isinstance(message, IMessage):
            raise RuntimeError(f'Unexpected message type {message}')
        if message.type == MessageType.COMMAND:
            return self._handle_command(command=message, **depends)
        elif message.type == MessageType.EVENT:
            return self._handle_event(event=message, **depends)
        raise RuntimeError(f'Only support command end event message handling. Got {message.type}')

    def _handle_command(self, command: IMessage, **depends):
        module = self._get_module_by_domain(command.domain)
        handler = module.get_command_handler(command)
        return self._executor.process_handler(handler, **depends)

    def _handle_event(self, event: IMessage, **depends):
        handlers = []
        for module in self._modules.values():
            handlers.extend(module.get_event_handlers(event))
        return self._executor.process_handlers(handlers, **depends)

    def _get_module_by_domain(self, domain: str) -> Module:
        if module := self._modules.get(domain):
            return module
        raise ValueError(f'Unregistered module for domain {domain}')


__context = None


def set_application(app: Application):
    global __context
    __context = app


def get_application():
    global __context
    return __context
