import inspect
from functools import partial
from typing import (
    Callable,
)

from application.condition import (
    none_condition,
)
from application.abstractions import (
    ICondition,
    IHandler,
    ICommandHandler,
    IPayloadConverter,
    ResolvedHandlerT,
)
from application.exceptions import FailedHandlerCondition
from domain.message import (
    IMessage,
    IMessageMeta,
)
from domain import DomainCommand


class EventHandler(IHandler):

    def __init__(self, handler: ICommandHandler):
        self._handler = handler
        self._converter: IPayloadConverter = lambda x: x
        self._condition = none_condition
        self._defaults = {}

    def set_defaults(self, defaults: dict):
        self._handler.set_defaults(defaults)

    def resolve(self, message: IMessage) -> ResolvedHandlerT:
        if not self._condition.check(message):
            raise FailedHandlerCondition(
                f'Failed check condition {self._condition.__class__.__name__} '
                f'with message {message.topic}:{message.to_json()}'
            )
        command_type = self._handler.get_command_type()
        message = command_type(**self._converter(message.to_dict()))
        return self._handler.resolve(message=message)

    def set_condition(self, condition: ICondition):
        self._condition = condition

    def set_converter(self, converter: IPayloadConverter):
        self._converter = converter

    @property
    def condition(self):
        return self._condition


class CommandHandler(ICommandHandler):
    def __init__(self, func: Callable):
        signature = self._get_signature(func)
        command_param = self._get_command_param(func, signature)
        self._func = func
        self._signature = signature
        self._command_param = command_param
        self._defaults = {}

    def set_defaults(self, defaults: dict):
        self._defaults = defaults

    def get_command_type(self) -> type[DomainCommand]:
        return self._command_param.annotation

    def resolve(self, message: IMessage) -> ResolvedHandlerT:
        depends = {
            self._command_param.name: self._command_param.annotation(**message.to_dict()),
        }
        for name, param in self._signature.parameters.items():
            if name in self._defaults:
                depends[name] = self._defaults[name]
        return partial(self._func, **depends)

    @staticmethod
    def _get_signature(func) -> inspect.Signature:
        return inspect.signature(func, locals=locals(), globals=globals())

    @staticmethod
    def _get_command_param(func, signature: inspect.Signature):
        for name, param in signature.parameters.items():
            if isinstance(param.annotation, IMessageMeta):
                return param
        raise AttributeError(f"Can not find command param for {func} with params {signature}")
