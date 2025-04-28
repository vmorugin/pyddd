import re


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
        self._part_of: DomainName | None = (
            DomainName(items[0]) if is_subdomain else None
        )

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
            raise ValueError(
                f'DomainName "{self}" has not allowed symbols in section "{value}"'
            )

    def __repr__(self):
        return f"DomainName('{self}')"

class _DomainErrorMeta(type):
    def __init__(cls, name, bases, namespace, domain: DomainName | str | None = None):
        super().__init__(name, bases, namespace, domain=domain)
        if cls.__module__ == __name__:
            return
        if domain is None:
            raise ValueError(f"required set domain name for error '{cls.__module__}.{cls.__name__}'")
        cls.__domain_name = DomainName(domain)

    @property
    def __domain_name__(cls) -> DomainName:
        return cls.__domain_name


class DomainError(Exception, metaclass=_DomainErrorMeta):
    def __init_subclass__(cls, domain: DomainName | str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
