import abc
import inspect
from typing import (
    Callable,
    Protocol,
    Mapping,
)

from domain.message import (
    IMessage,
    IMessageMeta,
)
from domain import DomainCommand


class IHandler(abc.ABC):
    @abc.abstractmethod
    def handle(self, message: IMessage, **kwargs):
        ...

    @abc.abstractmethod
    def set_defaults(self, defaults: dict):
        ...


class ICommandHandler(IHandler, abc.ABC):
    @abc.abstractmethod
    def get_command_parameter(self) -> inspect.Parameter:
        ...


class IPayloadConverter(Protocol):
    def __call__(self, payload: Mapping) -> Mapping:
        ...


class EventHandler(IHandler):

    def __init__(self, handler: ICommandHandler):
        self._handler = handler
        self._converter: IPayloadConverter = lambda x: x

    def set_converter(self, converter: IPayloadConverter):
        self._converter = converter

    def set_defaults(self, defaults: dict):
        self._handler.set_defaults(defaults)

    def handle(self, message: IMessage, **kwargs):
        command_parameter = self._handler.get_command_parameter()
        return self._handler.handle(
            message=command_parameter.annotation(**self._converter(message.to_dict())),
            **kwargs
        )


class CommandHandler(ICommandHandler):
    def __init__(self, func: Callable):
        signature = self._get_signature(func)
        command_param = self._get_command_param(func, signature)
        self._func = func
        self._signature = signature
        self._command_param = command_param
        self._defaults = {}

    def get_command_parameter(self) -> inspect.Parameter:
        return self._command_param

    def set_defaults(self, defaults: dict):
        self._defaults = defaults

    def get_command_type(self) -> type[DomainCommand]:
        return self._command_param.annotation

    @staticmethod
    def _get_signature(func) -> inspect.Signature:
        return inspect.signature(func, locals=locals(), globals=globals())

    @staticmethod
    def _get_command_param(func, signature: inspect.Signature):
        for name, param in signature.parameters.items():
            if isinstance(param.annotation, IMessageMeta):
                return param
        raise AttributeError(f"Can not find command param for {func} with params {signature}")

    def handle(self, message: IMessage, **kwargs):
        depends = {
            self._command_param.name: self._command_param.annotation(**message.to_dict()),
        }
        for name, param in self._signature.parameters.items():
            if name in self._defaults:
                depends[name] = self._defaults[name]
        return self._func(**depends | kwargs)
