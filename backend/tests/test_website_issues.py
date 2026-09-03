"""Website issue reporting — deliberately separate from PG-scoped issues,
and deliberately open to unauthenticated visitors (a login-page bug must be
reportable without being able to log in)."""

from rate_limit import limiter


def test_unauthenticated_visitor_can_report_a_website_issue(client):
    resp = client.post(
        "/api/website-issues",
        json={"description": "The login button does nothing on Safari."},
    )
    assert resp.status_code == 201


def test_description_is_required(client):
    resp = client.post("/api/website-issues", json={})
    assert resp.status_code == 422


def test_optional_fields_are_accepted(client):
    resp = client.post(
        "/api/website-issues",
        json={
            "description": "Page layout breaks at narrow widths.",
            "page_url": "https://example.com/user-dashboard.html",
            "reporter_email": "reporter@example.com",
        },
    )
    assert resp.status_code == 201


def test_website_issue_reporting_is_rate_limited(client):
    limiter.enabled = True
    try:
        statuses = [
            client.post("/api/website-issues", json={"description": "spam"}).status_code for _ in range(10)
        ]
    finally:
        limiter.enabled = False
    assert 429 in statuses


def test_is_not_group_scoped_and_not_visible_via_pg_issues_endpoint(make_client):
    """Confirms website issues are a genuinely separate concept from the
    PG-scoped `issues` table — reported via a different endpoint entirely,
    and not something an Owner's PG issue list would ever surface."""
    from tests.conftest import register_owner

    owner = make_client()
    register_owner(owner, "WebsiteIssueOwner", "WI PG")

    resp = owner.post("/api/website-issues", json={"description": "unrelated site bug"})
    assert resp.status_code == 201

    pg_issues = owner.get("/api/issues").json()
    assert pg_issues == []
