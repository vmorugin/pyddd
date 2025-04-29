import json
import re
import typing as t
import warnings
from contextlib import suppress
from enum import Enum
from types import MappingProxyType
import datetime as dt


class DomainName(str):
    """
    DomainName class represents a domain name string. It extends the built-in `str` class and adds validation for domain name format.

    Attributes:
        part_of (Optional[DomainName]): Gets the parent DomainName of a sub-domain.

    Raises:
        ValueError: If the domain name contains disallowed symbols.

    """

    def __new__(cls, value):
        if isinstance(value, cls):
            return value
        return super().__new__(cls, value)

    def __init__(self, value: str):
        items = value.rsplit(".", maxsplit=1)
        is_subdomain = len(items) != 1
        self._validate(items[1] if is_subdomain else items[0])
        self._part_of: DomainName | None = DomainName(items[0]) if is_subdomain else None

    @property
    def part_of(self):
        """
        Gets the parent DomainName of a sub-domain.

        Returns:
            (Optional[DomainName]): The parent DomainName instance or None if it's not a sub-domain.
        """
        return self._part_of

    def _validate(self, value: str):
        if not re.search(r"^([a-z]|[a-z0-9]-)+$", value):
            raise ValueError(f'DomainName "{self}" has not allowed symbols in section "{value}"')

    def __repr__(self):
        return f"DomainName('{self}')"


def get_domain_name(
    cls,
    bases: tuple[type],
    domain: DomainName | str | None = None,
) -> DomainName | None:
    domains: set[DomainName] = set()  # type: ignore
    for base in bases:
        with suppress(AttributeError):
            if getattr(base, "__domain_name__") is not None:
                domains.add(base.__domain_name__)  # type: ignore

    if len(domains) > 1:
        raise RuntimeError("Not allowed multiple inheritance domain")

    if len(domains) == 1 and domain is not None and domain != cls.__domain_name__:
        raise RuntimeError(f"not allowed replace domain name in child class: {cls.__module__}.{cls.__name__}")

    if len(domains) == 0 and domain is not None:
        return DomainName(domain)

    if len(domains) == 1 and (domain is None or domain == cls.__domain_name__):
        return cls.__domain_name__  # type: ignore

    return None


class _DomainErrorMeta(type):
    def __init__(cls, name, bases, namespace, domain: DomainName | str | None = None):
        super().__init__(name, bases, namespace, domain=domain)
        if cls.__module__ == __name__ and cls.__name__ == "DomainError":
            return
        domain_name = get_domain_name(cls, bases, domain)
        if domain_name is None:
            raise ValueError(f"required set domain name for error '{cls.__module__}.{cls.__name__}'")
        cls.__domain_name = domain_name

    @property
    def __domain_name__(cls) -> DomainName:
        return cls.__domain_name


class DomainError(Exception, metaclass=_DomainErrorMeta):
    __template__: str

    def __init_subclass__(cls, domain: DomainName | str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(self, __message: str | None = None, /, **kwargs):
        if __message is None:
            message = self.__template__.format_map(kwargs)
        else:
            message = __message
        super().__init__(message)


class JsonDict(dict):
    JSON_CONVERTER = json
    CONVERTABLE_TYPES = (bool, int, float, str, type(None))
    CONVERTERS: t.Mapping[type, t.Callable[[t.Any], t.Any]] = MappingProxyType(
        {
            dt.date: lambda x: x.isoformat(),
            Enum: lambda x: x.value,
        }
    )
    ITERABLE_CONVERTERS: t.Mapping[type[t.Iterable], t.Callable[[t.Iterable], t.Iterable]] = MappingProxyType(
        {tuple: tuple}
    )
    DEFAULT_ITERABLE_CONVERTER: t.Callable[[t.Iterable], t.Iterable] = list

    def __init__(self, __obj: t.Mapping | None = None, /, **kwargs):
        result = self._parse_object(kwargs if __obj is None else __obj)
        super().__init__(result)

    def _parse_object(self, obj: t.Mapping):
        result = {}
        markers = {id(obj): obj}
        for key, value in obj.items():
            result[key] = self._parse_value(value, markers)
        return result

    def _parse_mapping(self, obj: t.Mapping, markers: dict):
        marker_id = id(obj)
        if marker_id in markers:
            raise ValueError("Circular reference detected")
        markers[id(obj)] = obj

        result = self.__class__()
        for key, value in obj.items():
            dict.__setitem__(result, key, self._parse_value(value, markers))
        return result

    def _parse_iterable(self, values: t.Iterable, markers) -> t.Iterable:
        marker_id = id(values)
        if marker_id in markers:
            raise ValueError("Circular reference detected")
        markers[id(values)] = values

        result = [self._parse_value(value, markers) for value in values]
        return self._get_iterable_type(values)(result)

    def _get_iterable_type(self, values) -> t.Callable[[t.Iterable], t.Iterable]:
        for type_, converter in self.ITERABLE_CONVERTERS.items():
            if isinstance(values, type_):
                return converter
        if self.DEFAULT_ITERABLE_CONVERTER is None:
            return type(values)  # pragma: no cover
        return self.DEFAULT_ITERABLE_CONVERTER

    def _parse_value(self, value, markers: dict):
        if isinstance(value, self.CONVERTABLE_TYPES):
            return value
        elif isinstance(value, tuple(self.CONVERTERS.keys())):
            return self._parse_other(value)
        elif isinstance(value, t.Mapping):
            return self._parse_mapping(value, markers)
        elif isinstance(value, t.Iterable):
            return self._parse_iterable(value, markers)
        else:
            return str(value)

    def _parse_other(self, value):
        for type_, converter in self.CONVERTERS.items():
            if isinstance(value, type_):
                return converter(value)

    def __repr__(self):
        return super().__repr__()

    def __str__(self):
        return self.JSON_CONVERTER.dumps(self)

    def __setitem__(self, key, value):
        value = self._parse_value(value, {id(self): self})
        super().__setitem__(key, value)

    def setdefault(self, __key, __default=None):
        if __key not in self:
            self[__key] = __default
        return self[__key]

    def update(self, __m=None, **kwargs):
        if isinstance(__m, dict):
            __m = __m.items()
        if __m is not None:
            for key, value in __m:
                self[key] = value

        for key, value in kwargs.items():
            self[key] = value


class FrozenJsonDict(JsonDict):
    DEFAULT_ITERABLE_CONVERTER = tuple

    def __init__(self, __obj: t.Mapping | None = None, /, **kwargs):
        super().__init__(__obj, **kwargs)
        self.__hash = hash(str(self))

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __str__(self):
        if not hasattr(self, "__json"):
            setattr(self, "__json", super().__str__())
        return getattr(self, "__json")

    def update(self, __m=None, **kwargs):
        warnings.warn("Method not implemented", DeprecationWarning, stacklevel=2)
        raise NotImplementedError()

    def pop(self, __key):
        warnings.warn("Method not implemented", DeprecationWarning, stacklevel=2)
        raise NotImplementedError()

    def popitem(self):
        warnings.warn("Method not implemented", DeprecationWarning, stacklevel=2)
        raise NotImplementedError()

    def setdefault(self, __key, __default=None):
        warnings.warn("Method not implemented", DeprecationWarning, stacklevel=2)
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def clear(self):
        warnings.warn("Method not implemented", DeprecationWarning, stacklevel=2)
        raise NotImplementedError()

    def __hash__(self):
        return self.__hash
