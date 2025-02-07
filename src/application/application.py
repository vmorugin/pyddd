import logging
from collections import defaultdict

from application.executor import IExecutor, SyncExecutor
from application.module import Module
from domain.message import (
    IMessage,
    MessageType,
)


class Application:
    def __init__(
            self,
            logger_name: str = 'pyddd.application',
            sync_executor: IExecutor = None,
    ):
        self._modules: dict[str, Module] = {}
        self._defaults: dict[str, dict] = defaultdict(dict)
        self._logger = logging.getLogger(logger_name)
        self._executor = sync_executor or SyncExecutor()

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
        if message.type == MessageType.COMMAND:
            return self._handle_command(command=message, **depends)
        elif message.type == MessageType.EVENT:
            return self._handle_event(event=message, **depends)

    def _handle_command(self, command: IMessage, **depends):
        module = self._get_module_by_domain(command.domain)
        handler = module.get_command_handler(command.topic)
        return self._executor.process_command(command, handler, **depends)

    def _get_module_by_domain(self, domain: str) -> Module:
        if module := self._modules.get(domain):
            return module
        raise ValueError(f'Unregistered module for domain {domain}')

    def _handle_event(self, event: IMessage, **depends):
        handlers = []
        for module in self._modules.values():
            handlers.extend(module.get_event_handlers(event.topic))
        return self._executor.process_event(event, handlers, **depends)


__context = None


def set_application(app: Application):
    global __context
    __context = app


def get_application():
    global __context
    return __context
