import pytest

from pyddd.domain.types import (
    DomainName,
    DomainError,
)


class TestDomain:
    def test_could_eq_like_str(self):
        domain = DomainName("test")
        assert domain == "test"

    def test_could_be_str_separated(self):
        domain = DomainName("test.domain")
        assert domain == "test.domain"

    @pytest.mark.parametrize("domain", ('test--domain', 'test.domain:ru', 'test,domain, test_domain', '1', 'Camel'))
    def test_must_be_lowecase_digits_or_str(self, domain):
        with pytest.raises(ValueError):
            DomainName(domain)

class TestDomainError:
    def test_domain_error_must_be_subclass_of_exc(self):
        assert issubclass(DomainError, Exception)

    def test_has_domain_prop(self):
        class TestDomainError(DomainError, domain=DomainName("test")):
            ...

        assert TestDomainError.__domain_name__ == "test"

    def test_could_not_pass_empty_domain(self):
        with pytest.raises(ValueError):
            class TestDomainError(DomainError, domain=None):
                ...

    def test_could_not_pass_invalid_domain(self):
        with pytest.raises(ValueError):
            class TestDomainError(DomainError, domain='test___asd'):
                ...

    def test_could_impl_base_class(self):
        class TestDomainError(DomainError, domain=DomainName("test")):
            ...

        class SecondError(TestDomainError):
            ...

        assert TestDomainError.__domain_name__ == "test"

