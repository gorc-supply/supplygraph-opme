"""The single connection helper must always verify TLS certificates and hostnames (no network needed;
runs on Windows, Linux CI and Streamlit Cloud alike). See docs/decisions/ADR-014-tls-certifi.md."""

from __future__ import annotations

import ssl

import certifi
import pytest

from supplygraph.db import driver_args, tls_context


def test_tls_context_always_verifies():
    ctx = tls_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_tls_context_includes_certifi_roots():
    ctx = tls_context()
    certifi_only = ssl.create_default_context(cafile=certifi.where())
    assert ctx.cert_store_stats()["x509_ca"] >= certifi_only.cert_store_stats()["x509_ca"] > 0


@pytest.mark.parametrize(("uri", "expected"), [
    ("neo4j+s://abc123.databases.neo4j.io", "neo4j://abc123.databases.neo4j.io"),
    ("bolt+s://abc123.databases.neo4j.io:7687", "bolt://abc123.databases.neo4j.io:7687"),
])
def test_secure_uris_get_verified_context(uri, expected):
    new_uri, kwargs = driver_args(uri)
    assert new_uri == expected
    ctx = kwargs["ssl_context"]
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


def test_plain_local_uri_unchanged():
    assert driver_args("neo4j://localhost:7687") == ("neo4j://localhost:7687", {})


@pytest.mark.parametrize("uri", ["neo4j+ssc://x.databases.neo4j.io", "bolt+ssc://x:7687"])
def test_self_signed_schemes_are_refused(uri):
    with pytest.raises(ValueError, match="ssc"):
        driver_args(uri)
