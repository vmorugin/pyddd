from collections import defaultdict

from application.module import Module
from domain.message import (
    IMessage,
    MessageType,
)


class Application:
    def __init__(self):
        self._modules: dict[str, Module] = {}
        self._defaults: dict[str, dict] = defaultdict(dict)

    def set_defaults(self, domain: str, **kwargs):
        self._defaults[domain].update(kwargs)

    def include(self, module: Module):
        if module.domain in self._modules:
            raise ValueError("Already registered domain 'test'")

        module.set_defaults(self._defaults[module.domain])
        self._modules[module.domain] = module

    def handle(self, message: IMessage, **kwargs):
        module = self._modules.get(message.domain)
        if message.type == MessageType.COMMAND:
            if not module:
                raise ValueError(f'Unregistered module for domain {message.domain}')
            return module.handle_command(message, **kwargs)
        elif message.type == MessageType.EVENT:
            if not module:
                # todo: log
                return
            module.handle_event(message, **kwargs)
