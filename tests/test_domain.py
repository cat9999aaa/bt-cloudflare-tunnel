from __future__ import annotations

import pytest

from cf_tunnel.domain import DomainValidationError, parse_wildcard_domain


def test_parse_wildcard_domain_accepts_deep_subdomain() -> None:
    wildcard = parse_wildcard_domain("*.dev.dashen.wang")

    assert wildcard.value == "*.dev.dashen.wang"
    assert wildcard.hostname == "dev.dashen.wang"


@pytest.mark.parametrize(
    "raw",
    ["dashen.wang", "https://dashen.wang", "*.dashen.wang:443", "*.", "*. bad.com"],
)
def test_parse_wildcard_domain_rejects_non_wildcard_fqdn(raw: str) -> None:
    with pytest.raises(DomainValidationError):
        parse_wildcard_domain(raw)
