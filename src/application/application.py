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
        if module := self._modules.get(domain):
            module.set_defaults(kwargs)

    def include(self, module: Module):
        if module.domain in self._modules:
            raise ValueError("Already registered domain 'test'")

        module.set_defaults(self._defaults[module.domain])
        self._modules[module.domain] = module

    def handle(self, message: IMessage, **kwargs):
        if message.type == MessageType.COMMAND:
            module = self._modules.get(message.domain)
            if not module:
                raise ValueError(f'Unregistered module for domain {message.domain}')
            return module.handle_command(message, **kwargs)
        elif message.type == MessageType.EVENT:
            result = []
            for module in self._modules.values():
                if module.can_handle(message):
                    result.extend(module.handle_event(message, **kwargs))
            return result


__context = None


def set_application(app: Application):
    global __context
    __context = app


def get_application():
    global __context
    return __context
