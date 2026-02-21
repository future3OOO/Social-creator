"""Tests for scraper URL validation helpers."""

import pytest

from utils import validate_trademe_url


def testvalidate_trademe_url_accepts_primary_host():
    url = "https://www.trademe.co.nz/a/property/residential/rent/listing/1234567890"
    assert validate_trademe_url(url) == url


def testvalidate_trademe_url_accepts_subdomain():
    url = "https://trademe.co.nz/a/property/residential/rent/listing/1234567890"
    assert validate_trademe_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/trademe.co.nz/listing/123",
        "ftp://trademe.co.nz/listing/123",
        "notaurl",
    ],
)
def testvalidate_trademe_url_rejects_non_trademe_hosts_or_invalid_scheme(url: str):
    with pytest.raises(ValueError, match="trademe.co.nz|http\\(s\\) TradeMe"):
        validate_trademe_url(url)
