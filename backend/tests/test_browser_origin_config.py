"""Tests for the localhost/127.0.0.1 browser-auth configuration fix.

These guard the specific bug: a frontend opened via one of the two
conventional local hostnames (localhost vs 127.0.0.1) must work identically,
because the auth cookie is SameSite=Strict and browsers treat those two
hostnames as different sites.
"""

from config import Settings
from tests.conftest import unique_email


def test_cors_default_allows_both_local_hostnames():
    """The hardcoded class default (used if .env fails to load for any
    reason) must not silently under-allow one of the two hostnames."""
    default = Settings.model_fields["cors_origins"].default
    assert "http://localhost:5500" in default
    assert "http://127.0.0.1:5500" in default


def test_cors_preflight_allows_localhost_origin(client):
    resp = client.options(
        "/api/auth/me",
        headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5500"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_allows_127_origin(client):
    resp = client.options(
        "/api/auth/me",
        headers={"Origin": "http://127.0.0.1:5500", "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_rejects_untrusted_origin(client):
    resp = client.options(
        "/api/auth/me",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_login_cookie_is_httponly_strict_and_host_only(client):
    """Verifies the cookie itself hasn't been weakened: still HttpOnly and
    SameSite=Strict, still host-only (no explicit Domain=), and not marked
    Secure under the non-production test environment (which serves plain
    HTTP, so a Secure cookie would never be sent at all)."""
    email = unique_email("cookiecheck")
    resp = client.post(
        "/api/auth/register/owner",
        json={"name": "Cookie Check", "email": email, "password": "password123", "pg_name": "Cookie PG"},
    )
    assert resp.status_code == 201

    set_cookie = resp.headers.get("set-cookie")
    assert set_cookie is not None
    lowered = set_cookie.lower()

    assert "httponly" in lowered
    assert "samesite=strict" in lowered
    assert "domain=" not in lowered
    assert "secure" not in lowered  # test/dev environment is not_production


def test_samesite_none_forces_secure_even_outside_production(client, monkeypatch):
    """Production readiness guard: a deployment that sets COOKIE_SAMESITE=none
    (frontend/API on unrelated domains) must get a Secure cookie regardless
    of ENVIRONMENT — browsers reject SameSite=None without Secure anyway, but
    this must not depend on remembering to also set ENVIRONMENT=production."""
    monkeypatch.setattr("routes.auth.settings.cookie_samesite", "none")

    email = unique_email("samesitenone")
    resp = client.post(
        "/api/auth/register/owner",
        json={"name": "SameSite None Check", "email": email, "password": "password123", "pg_name": "X PG"},
    )
    assert resp.status_code == 201

    set_cookie = resp.headers.get("set-cookie", "").lower()
    assert "samesite=none" in set_cookie
    assert "secure" in set_cookie
