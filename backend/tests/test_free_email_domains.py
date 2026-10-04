"""
YET-243: FREE_EMAIL_DOMAINS must cover common mailbox-provider variants and
subdomains, otherwise an org can claim (and DNS-"verify") a domain that anyone
can register an address on.
"""

import pytest

from app.services.organization import FREE_EMAIL_DOMAINS, is_free_email_domain

LISTED = [
    "gmail.com",
    "googlemail.com",
    "live.com",
    "msn.com",
    "hotmail.com",
    "hotmail.co.uk",
    "outlook.com",
    "yahoo.com",
    "yahoo.co.uk",
    "ymail.com",
    "gmx.com",
    "gmx.net",
    "gmx.de",
    "aol.com",
    "proton.me",
    "pm.me",
    "protonmail.com",
    "icloud.com",
    "mail.ru",
    "yandex.ru",
    "mynet.com",
]


@pytest.mark.parametrize("domain", LISTED)
def test_known_free_providers_are_rejected(domain):
    assert is_free_email_domain(domain)


@pytest.mark.parametrize("domain", ["GMAIL.COM", "Gmail.Com.", " gmail.com "])
def test_case_trailing_dot_and_whitespace_are_normalised(domain):
    assert is_free_email_domain(domain)


@pytest.mark.parametrize("domain", ["mail.gmail.com", "a.b.outlook.com"])
def test_subdomains_of_free_providers_are_rejected(domain):
    assert is_free_email_domain(domain)


@pytest.mark.parametrize(
    "domain",
    ["acme.example", "bilgi.edu.tr", "notgmail.com", "gmail.com.evil.example", "mygmx.net"],
)
def test_real_or_lookalike_domains_are_not_treated_as_free(domain):
    assert not is_free_email_domain(domain)


def test_all_listed_entries_are_lowercase_without_trailing_dot():
    assert all(d == d.lower().strip(".") for d in FREE_EMAIL_DOMAINS)
