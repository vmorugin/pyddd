import pytest

from application import Application
from application import Module
from application.application import (
    set_application,
    get_application,
)

from domain import (
    DomainCommand,
    DomainEvent,
)


class TestCommand(DomainCommand, domain='test'):
    ...


class TestEvent(DomainEvent, domain='test'):
    ...


class TestApplication:
    def test_include_twice(self):
        app = Application()
        app.include(Module('test'))
        with pytest.raises(ValueError, match="Already registered domain 'test'"):
            app.include(Module('test'))

    def test_handle_command(self):
        def foo(cmd: TestCommand):
            return True

        app = Application()
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(TestCommand())
        assert result is True

    def test_handle_event(self):
        def foo(cmd: TestCommand):
            return 1

        app = Application()
        module = Module('test')
        module.subscribe(TestEvent.__topic__)(foo)
        app.include(module)
        result = app.handle(TestEvent())
        assert result == [1]

    def test_handle_unresolved_event(self):
        app = Application()
        app.handle(TestEvent())

    def test_handle_unresolved_command(self):
        app = Application()
        with pytest.raises(ValueError, match='Unregistered module for domain'):
            app.handle(TestCommand())

    def test_handle_with_defaults(self):
        def foo(cmd: TestCommand, atr: str):
            return atr

        app = Application()
        app.set_defaults('test', atr='success')
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(TestCommand())
        assert result == 'success'

    def test_handle_with_overwrite_defaults(self):
        def foo(cmd: TestCommand, atr: str):
            return atr

        app = Application()
        app.set_defaults('test', atr='fail')
        module = Module('test')
        module.register(foo)
        app.include(module)
        result = app.handle(TestCommand(), atr='success')
        assert result == 'success'

def test_set_and_get_application():
    app = Application()
    set_application(app)
    assert get_application() == app
