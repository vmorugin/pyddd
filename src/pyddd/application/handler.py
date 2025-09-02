import inspect
from functools import partial
import typing as t

from pyddd.application.condition import (
    none_condition,
)
from pyddd.application.abstractions import (
    ICondition,
    IHandler,
    ICommandHandler,
    IPayloadConverter,
    AnyCallable,
    IRetryStrategy,
)
from pyddd.application.exceptions import FailedHandlerCondition
from pyddd.application.retry import none_retry
from pyddd.domain.abstractions import (
    IMessage,
)
from pyddd.domain.command import DomainCommand


class EventHandler(IHandler):
    def __init__(self, handler: ICommandHandler):
        self._handler = handler
        self._converter: IPayloadConverter = lambda x: x
        self._condition: ICondition = none_condition
        self._retry_strategy: IRetryStrategy = none_retry
        self._defaults: dict[str, t.Any] = {}

    def set_defaults(self, defaults: dict):
        self._handler.set_defaults(defaults)

    def resolve(self, message: IMessage) -> AnyCallable:
        if not self._condition.check(message):
            raise FailedHandlerCondition(
                f"Failed check condition {self._condition.__class__.__name__} "
                f"with message {message.__topic__}:{message.to_json()}"
            )
        command_type = self._handler.get_command_type()
        message = command_type(**self._converter(message.to_dict()))
        return self._retry_strategy(self._handler.resolve(message=message))

    def set_condition(self, condition: ICondition):
        self._condition = condition

    def set_converter(self, converter: IPayloadConverter):
        self._converter = converter

    def set_retry_strategy(self, strategy: IRetryStrategy):
        self._retry_strategy = strategy


class CommandHandler(ICommandHandler):
    def __init__(self, func: t.Callable):
        signature = self._get_signature(func)
        command_param = self._get_command_param(func, signature)
        self._func = func
        self._signature = signature
        self._command_param = command_param
        self._defaults: dict[str, t.Any] = {}

    def set_defaults(self, defaults: dict):
        self._defaults = defaults

    def get_command_type(self) -> type[DomainCommand]:
        return self._command_param.annotation

    def resolve(self, message: IMessage) -> AnyCallable:
        depends = {
            self._command_param.name: self._command_param.annotation.load(message),
        }
        for name, param in self._signature.parameters.items():
            if name in self._defaults:
                depends[name] = self._defaults[name]
        return partial(self._func, **depends)

    @staticmethod
    def _get_signature(func) -> inspect.Signature:
        return inspect.signature(func)

    @staticmethod
    def _get_command_param(func, signature: inspect.Signature):
        hint = t.get_type_hints(func)
        for name, param in signature.parameters.items():
            annotation = hint[name]
            if issubclass(annotation, DomainCommand):
                return inspect.Parameter(name, param.kind, annotation=annotation, default=param.default)
        raise AttributeError(f"Can not find command param for {func} with params {signature}")
