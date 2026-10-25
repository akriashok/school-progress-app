PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _upload(client, h, data=PNG, name="a.png", mime="image/png"):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/school/website/images", headers=h, files={"file": (name, data, mime)})


def test_default_content_before_editing(client, world) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/api/v1/public/schools/scha/website")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "School SCHA" and body["website"]["tagline"] == "Welcome to School SCHA"
    assert len(body["website"]["facilities"]) == 4


def test_admin_edits_and_public_sees_it(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.a.h("admin")
    img = _upload(client, h).json()["image_id"]
    content = {
        "tagline": "Learning with joy",
        "hero_title": "Where children shine",
        "hero_image": img,
        "stats": [{"value": "1200+", "label": "Students"}],
        "gallery": [{"image": img, "caption": "Sports day"}],
        "leaders": [{"name": "Dr. Rao", "role": "Principal", "photo": img}],
        "contact": {"whatsapp": "98765 43210", "instagram": "https://instagram.com/school"},
        "theme": {"primary": "#0f766e", "accent": "#f97316"},
    }
    r = client.put("/api/v1/school/website", headers=h, json=content)
    assert r.status_code == 200, r.text
    assert r.json()["contact"]["whatsapp"] == "+919876543210"
    pub = client.get("/api/v1/public/schools/SCHA/website").json()["website"]
    assert pub["hero_title"] == "Where children shine" and pub["gallery"][0]["caption"] == "Sports day"
    img_r = client.get(f"/api/v1/public/schools/SCHA/images/{img}")
    assert img_r.status_code == 200 and img_r.content == PNG and img_r.headers["content-type"] == "image/png"


def test_images_are_scoped_to_their_school(client, world) -> None:  # type: ignore[no-untyped-def]
    img = _upload(client, world.a.h("admin")).json()["image_id"]
    # School B cannot serve or reference school A's image
    assert client.get(f"/api/v1/public/schools/SCHB/images/{img}").status_code == 404
    r = client.put("/api/v1/school/website", headers=world.b.h("admin"), json={"hero_image": img})
    assert r.status_code == 422
    # Path tricks are rejected
    assert client.get("/api/v1/public/schools/SCHA/images/..%2F..%2Fsecret.png").status_code == 404


def test_only_school_admin_can_edit(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    assert client.get("/api/v1/school/website", headers=a.h("principal")).status_code == 200
    for who in ("principal", "teacher1", "parent1", "student_s1"):
        assert client.put("/api/v1/school/website", headers=a.h(who), json={}).status_code == 403
        assert _upload(client, a.h(who)).status_code == 403


def test_validation(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.a.h("admin")
    bad = [
        {"hero_image": "https://evil.example/x.png"},  # only our own image ids
        {"contact": {"facebook": "http://facebook.com/x"}},  # https only
        {"contact": {"facebook": "javascript:alert(1)"}},
        {"theme": {"primary": "red"}},
        {"stats": [{"value": "1", "label": "a"}] * 5},
    ]
    for body in bad:
        assert client.put("/api/v1/school/website", headers=h, json=body).status_code == 422, body
    assert _upload(client, h, data=b"GIF89a", name="x.png").status_code == 422
    assert _upload(client, h, data=b"%PDF", name="x.pdf", mime="application/pdf").status_code == 422


def test_inactive_school_site_is_hidden(client, world) -> None:  # type: ignore[no-untyped-def]
    client.patch(f"/api/v1/admin/schools/{world.a.school_id}", headers=world.platform(), json={"is_active": False})
    assert client.get("/api/v1/public/schools/SCHA/website").status_code == 404
