"""CSRF backstop via Origin-header validation.

Discovered during the final release audit: the live production deployment
has COOKIE_SAMESITE=none configured (required because the frontend and API
are on two separate *.onrender.com subdomains, which browsers treat as
cross-site — onrender.com is on the Public Suffix List). SameSite=None
deliberately sends the auth cookie cross-site, so it provides none of the
CSRF protection SameSite=Strict/Lax give automatically. CORS does not close
this gap either: CORS only blocks a cross-site script from *reading* a
response, not from *sending* a state-changing request — a classic hidden
<form method="POST" enctype="multipart/form-data"> targeting the issue or
document upload endpoints is completely unaffected by CORS.

These tests verify the Origin-validation middleware added in main.py.
"""

from tests.conftest import join_and_approve, register_owner, register_user

TRUSTED_ORIGIN = "http://localhost:5500"
UNTRUSTED_ORIGIN = "https://evil.example.com"


def test_mutation_with_no_origin_header_is_unaffected(client):
    """Regression: non-browser clients (curl, server-to-server, the test
    suite itself) don't send an Origin header on a same-origin-shaped
    request and must not be blocked — they are not a CSRF vector."""
    resp = register_owner(client, "NoOriginOwner", "No Origin PG")
    assert resp  # register_owner already asserts 201 internally


def test_mutation_with_trusted_origin_succeeds(make_client):
    client = make_client()
    resp = client.post(
        "/api/auth/register/owner",
        json={"name": "TrustedOrigin", "email": "trusted-origin@example.com", "password": "password123", "pg_name": "Trusted PG"},
        headers={"Origin": TRUSTED_ORIGIN},
    )
    assert resp.status_code == 201


def test_mutation_with_untrusted_origin_is_rejected(make_client):
    client = make_client()
    resp = client.post(
        "/api/auth/register/owner",
        json={"name": "Attacker", "email": "attacker@example.com", "password": "password123", "pg_name": "Evil PG"},
        headers={"Origin": UNTRUSTED_ORIGIN},
    )
    assert resp.status_code == 403


def test_get_request_with_untrusted_origin_is_not_blocked(make_client):
    """Read-only requests are not a CSRF target — only state-changing
    methods are checked."""
    client = make_client()
    register_owner(client, "ReadOnlyOwner", "Read Only PG")
    resp = client.get("/api/auth/me", headers={"Origin": UNTRUSTED_ORIGIN})
    assert resp.status_code == 200


def test_forged_cross_site_issue_submission_is_rejected(make_client):
    """The specific vulnerable case: a classic cross-site multipart form
    POST — exactly what CORS does not protect against — must still be
    rejected by the Origin check."""
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "IssueCSRFOwner", "Issue CSRF PG")
    register_user(user, "IssueCSRFUser")
    join_and_approve(owner, user, group["access_key"])

    forged = user.post(
        "/api/issues",
        data={"category": "plumbing", "description": "forged via cross-site form"},
        headers={"Origin": UNTRUSTED_ORIGIN},
    )
    assert forged.status_code == 403

    legitimate = user.post(
        "/api/issues",
        data={"category": "plumbing", "description": "real submission"},
        headers={"Origin": TRUSTED_ORIGIN},
    )
    assert legitimate.status_code == 201


def test_forged_cross_site_document_upload_is_rejected(make_client):
    owner = make_client()
    group = register_owner(owner, "DocCSRFOwner", "Doc CSRF PG")

    forged = owner.post(
        "/api/documents",
        data={"title": "forged", "category": "other"},
        files={"file": ("x.pdf", b"%PDF-1.4\n%fake", "application/pdf")},
        headers={"Origin": UNTRUSTED_ORIGIN},
    )
    assert forged.status_code == 403
