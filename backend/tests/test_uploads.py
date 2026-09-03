from tests.conftest import join_and_approve, register_owner, register_user

_REAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS"
    b"\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_valid_image_upload_accepted(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "User1")
    join_and_approve(owner, user, group["access_key"])

    resp = user.post(
        "/api/issues",
        data={"category": "plumbing", "description": "Leak"},
        files={"image": ("photo.png", _REAL_PNG, "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["image_path"] is not None


def test_fake_image_rejected_by_content_sniffing(make_client):
    owner = make_client()
    user = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user, "User1")
    join_and_approve(owner, user, group["access_key"])

    resp = user.post(
        "/api/issues",
        data={"category": "plumbing", "description": "Leak"},
        # Text content with a .jpg filename and a spoofed image/jpeg content-type
        files={"image": ("photo.jpg", b"this is not an image", "image/jpeg")},
    )
    assert resp.status_code == 422


def test_only_own_issue_image_is_fetchable(make_client):
    owner = make_client()
    user1 = make_client()
    user2 = make_client()
    group = register_owner(owner, "Owner", "Test PG")
    register_user(user1, "User1")
    register_user(user2, "User2")
    join_and_approve(owner, user1, group["access_key"])
    join_and_approve(owner, user2, group["access_key"])

    created = user1.post(
        "/api/issues",
        data={"category": "plumbing", "description": "Leak"},
        files={"image": ("photo.png", _REAL_PNG, "image/png")},
    ).json()

    assert user1.get(f"/api/issues/{created['id']}/image").status_code == 200
    assert user2.get(f"/api/issues/{created['id']}/image").status_code == 404
    assert owner.get(f"/api/issues/{created['id']}/image").status_code == 200


def test_document_upload_rejects_disallowed_type(make_client):
    owner = make_client()
    register_owner(owner, "Owner", "Test PG")

    resp = owner.post(
        "/api/documents",
        data={"title": "Bad file", "category": "other"},
        files={"file": ("virus.exe", b"MZ\x90\x00fakeexe", "application/octet-stream")},
    )
    assert resp.status_code == 422
