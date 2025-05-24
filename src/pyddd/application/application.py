import contextlib
import functools
import inspect
import logging
import typing as t
import warnings
from collections import defaultdict
from contextlib import suppress
from typing import (
    AsyncContextManager,
    ContextManager,
)

from pyddd.application.executor import (
    SyncExecutor,
    AsyncExecutor,
)
from pyddd.application.abstractions import (
    IExecutor,
    IApplication,
    ApplicationSignal,
    SignalListener,
    IModule,
    AnyCallable,
    Lifespan,
)
from pyddd.application.signal_manager import SignalManager
from pyddd.domain.abstractions import (
    MessageType,
    IMessage,
)


class Application(IApplication):
    def __init__(
        self,
        lifespan: Lifespan = None,
        logger_name: str = "pyddd.application",
        executor: IExecutor = None,
    ):
        self._modules: dict[str, IModule] = {}
        self._defaults: dict[str, dict] = defaultdict(dict)
        self._logger = logging.getLogger(logger_name)
        self._executor = executor
        self._is_running = False
        self._is_stopped = False
        self._lifespan_context = _build_lifespan(lifespan)(self)
        self._lifespan = None
        self._signal_manager = SignalManager()

    def set_defaults(self, domain: str, **kwargs):
        self._defaults[domain].update(kwargs)
        if module := self._modules.get(domain):
            module.set_defaults(kwargs)

    def include(self, module: IModule):
        if module.domain in self._modules:
            raise ValueError("Already registered domain 'test'")

        module.set_defaults(self._defaults[module.domain])
        self._modules[module.domain] = module

    async def run_async(self):
        if self._is_stopped:
            raise RuntimeError("Can not run. Application was stopped.")

        if self._executor is None:
            self._executor = AsyncExecutor()

        self._lifespan = _wrap_async_ctx_manager(self._lifespan_context)

        await self._signal_manager.notify_async(ApplicationSignal.BEFORE_RUN, self)
        await anext(self._lifespan)
        self._is_running = True

        await self._signal_manager.notify_async(ApplicationSignal.AFTER_RUN, self)

        set_application(self)

    async def stop_async(self):
        if not self._is_running:
            raise RuntimeError("Can not stop not running application")

        await self._signal_manager.notify_async(ApplicationSignal.BEFORE_STOP, self)

        self._is_running = False
        with suppress(StopAsyncIteration):
            await anext(self._lifespan)
        self._is_stopped = True

        await self._signal_manager.notify_async(ApplicationSignal.AFTER_STOP, self)

    def run(self):
        if self._is_stopped:
            raise RuntimeError("Can not run. Application was stopped.")

        if self._executor is None:
            self._executor = SyncExecutor()

        self._lifespan = _wrap_sync_ctx_manager(self._lifespan_context)

        self._signal_manager.notify(ApplicationSignal.BEFORE_RUN, self)

        self._is_running = True
        next(self._lifespan)

        self._signal_manager.notify(ApplicationSignal.AFTER_RUN, self)

        set_application(self)

    def stop(self):
        if not self._is_running:
            raise RuntimeError("Can not stop not running application")

        self._signal_manager.notify(ApplicationSignal.BEFORE_STOP, self)

        self._is_running = False

        with suppress(StopIteration):
            next(self._lifespan)

        self._is_stopped = True

        self._signal_manager.notify(ApplicationSignal.AFTER_STOP, self)

    def subscribe(self, signal: ApplicationSignal, listener: SignalListener):
        self._signal_manager.subscribe(signal, listener)

    def unsubscribe(self, signal: ApplicationSignal, listener: SignalListener):
        self._signal_manager.unsubscribe(signal, listener)

    @property
    def is_running(self):
        return self._is_running

    @property
    def is_stopped(self):
        return self._is_stopped

    def handle(self, message: IMessage, **depends):
        if not self._is_running:
            raise RuntimeError(f"Can not handle {message.__topic__}. App is not running!")
        if not isinstance(message, IMessage):
            raise RuntimeError(f"Unexpected message type {message}")
        if message.__type__ == MessageType.COMMAND:
            return self._handle_command(command=message, **depends)
        elif message.__type__ == MessageType.EVENT:
            return self._handle_event(event=message, **depends)
        raise RuntimeError(f"Only support command end event message handling. Got {message.__type__}")

    def _handle_command(self, command: IMessage, **depends):
        module = self._get_module_by_domain(command.__domain__)
        handler = module.get_command_handler(command)
        return self._executor.process_handler(handler, **depends)  # type: ignore[union-attr]

    def _handle_event(self, event: IMessage, **depends):
        handlers: list[AnyCallable] = []
        for module in self._modules.values():
            handlers.extend(module.get_event_handlers(event))
        return self._executor.process_handlers(handlers, **depends)  # type: ignore[union-attr]

    def _get_module_by_domain(self, domain: str) -> IModule:
        if module := self._modules.get(domain):
            return module
        raise ValueError(f"Unregistered module for domain {domain}")


async def _wrap_async_ctx_manager(context: AsyncContextManager):
    async with context:
        yield


def _wrap_sync_ctx_manager(context: ContextManager):
    with context:
        yield


class _DefaultLifespan:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, *exc_info: object) -> None:
        pass

    def __call__(self, mb: object):
        return self


_T = t.TypeVar("_T")


class _AsyncLiftContextManager(t.AsyncContextManager[_T]):
    def __init__(self, cm: t.ContextManager[_T]):
        self._cm = cm

    async def __aenter__(self) -> _T:
        return self._cm.__enter__()

    async def __aexit__(self, exc_type, exc_value, traceback) -> bool | None:
        return self._cm.__exit__(exc_type, exc_value, traceback)


def _wrap_gen_lifespan_context(
    lifespan_context: t.Callable[[t.Any], t.Generator],
) -> t.Callable[[t.Any], t.AsyncContextManager | t.ContextManager]:
    manager = contextlib.contextmanager(lifespan_context)

    @functools.wraps(manager)
    def wrapper(mb: t.Any) -> _AsyncLiftContextManager:
        return _AsyncLiftContextManager(manager(mb))

    return wrapper


def _build_lifespan(lifespan: Lifespan[IApplication] | None) -> Lifespan:
    if lifespan is None:
        return _DefaultLifespan()

    elif inspect.isasyncgenfunction(lifespan):
        warnings.warn(
            "async generator function lifespans are deprecated, "
            "use an @contextlib.asynccontextmanager function instead",
            DeprecationWarning,
        )
        return contextlib.asynccontextmanager(lifespan)  # type: ignore[arg-type]
    elif inspect.isgeneratorfunction(lifespan):
        warnings.warn(
            "generator function lifespans are deprecated, use an @contextlib.asynccontextmanager function instead",
            DeprecationWarning,
        )
        return _wrap_gen_lifespan_context(lifespan)  # type: ignore[arg-type]

    else:
        return lifespan


__context = None


def set_application(app: IApplication):
    global __context
    __context = app


def get_application() -> t.Optional[IApplication]:
    return __context


def get_running_application() -> IApplication:
    if isinstance(__context, Application) and __context.is_running:
        return __context
    raise RuntimeError("No running application")
