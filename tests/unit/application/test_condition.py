import pytest

from pyddd.application.condition import (
    NoneCondition,
    HasAttrs,
    And,
    Or,
    Not,
    Equal,
    none_condition,
)
from pyddd.domain.event import DomainEvent
from pyddd.domain.message import (
    Message,
    MessageType,
)


class ExampleEvent(DomainEvent, domain="test"): ...


def test_always_true_to_none_condition():
    condition = NoneCondition()
    assert condition.check(ExampleEvent()) is True


@pytest.mark.parametrize(
    "attrs, payload, expected",
    (
        (["reference"], {"reference": "123"}, True),
        (["reference"], {"id": 123}, False),
        (["reference", "name"], {"name": 123}, False),
        (["reference", "name"], {"name": 123, "reference": 1}, True),
        (["reference", "name"], {}, False),
    ),
)
def test_has_attribute_condition(attrs, payload, expected):
    message = Message(full_name="test.Event", message_type=MessageType.EVENT, payload=payload)
    condition = HasAttrs(*attrs)
    assert condition.check(message) is expected


def test_and_condition():
    event = Message("test.ExampleEvent", "EVENT", payload=dict(key1=123, key2="xyz", key3=True))

    condition = And(HasAttrs("key1"), HasAttrs("key2", "key3"))
    assert condition.check(event) is True

    condition = And(condition, HasAttrs("key4"))
    assert condition.check(event) is False


def test_or_condition():
    event = Message("test.ExampleEvent", "EVENT", payload=dict(key1=123, key2="xyz", key3=True))

    condition = Or(HasAttrs("key1"), HasAttrs("key2", "key3"))
    assert condition.check(event) is True

    condition = Or(HasAttrs("key4"), condition)
    assert condition.check(event) is True

    condition = And(HasAttrs("key4"), HasAttrs("key5"))
    assert condition.check(event) is False


@pytest.mark.parametrize("value", (1, "a", True, None))
def test_fail_use_not_condition_class_in_or_condition(value):
    with pytest.raises(TypeError):
        Or(value)


def test_not_condition():
    event = Message("test.ExampleEvent", "EVENT", payload=dict(key1=123, key2="xyz", key3=True))

    condition = Not(HasAttrs("key1"))
    assert condition.check(event) is False

    condition = Not(HasAttrs("key4"))
    assert condition.check(event) is True


@pytest.mark.parametrize("value", (1, "a", True, None))
def test_fail_use_not_condition_class_in_not_condition(value):
    with pytest.raises(TypeError):
        Not(value)


def test_equal_condition():
    event = Message("test.ExampleEvent", "EVENT", payload=dict(key1=123, key2="xyz", key3=True))

    condition = Equal(key1=123, key2="xyz", key3=True)
    assert condition.check(event) is True

    condition = Equal(key1=123, key2="xyz", key3=True, key4=None)
    assert condition.check(event) is False

    condition = Equal(key1=456, key2="xyz", key3=True)
    assert condition.check(event) is False

    condition = Equal(key1=123, key2="abc", key3=True)
    assert condition.check(event) is False

    condition = Equal(key1=123, key2="xyz", key3=False)
    assert condition.check(event) is False


def test_null_condition():
    event = Message("test.ExampleEvent", "EVENT", payload=dict(key1=123, key2="xyz", key3=True))
    assert none_condition.check(event) is True
    event = Message("test.ExampleEvent", "EVENT", payload={})
    assert none_condition.check(event) is True
