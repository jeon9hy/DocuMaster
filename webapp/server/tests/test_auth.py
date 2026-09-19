"""단일 Owner 인증 · Guest 읽기 전용 · PIN 원문이 저장소에 없음."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from app.auth import SESSION_COOKIE, hash_pin, verify_pin
from app.main import create_app
from fastapi.testclient import TestClient

from .conftest import TEST_PIN, create_project, login

WEBAPP = Path(__file__).resolve().parents[2]


def test_pin_hash_roundtrip_and_format():
    stored = hash_pin("123456")
    assert stored.startswith("scrypt$") and "123456" not in stored
    assert verify_pin("123456", stored)
    assert not verify_pin("123457", stored)
    assert not verify_pin("123456", "garbage")


def test_login_sets_httponly_cookie_and_logout_clears_it(guest):
    assert guest.get("/api/auth/session").json()["authenticated"] is False
    response = guest.post("/api/auth/login", json={"pin": TEST_PIN})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    # 응답 본문에는 토큰이 없다(프론트엔드가 저장할 값이 없음)
    assert SESSION_COOKIE not in response.text and response.json()["profile"]["nickname"]
    assert guest.get("/api/auth/session").json()["authenticated"] is True

    guest.post("/api/auth/logout")
    assert guest.get("/api/auth/session").json()["authenticated"] is False
    assert guest.post("/api/projects", json={"name": "x", "mode": "auto"}).status_code == 401


def test_wrong_pin_is_rejected_and_locks_after_five_failures(guest):
    for _ in range(4):
        wrong = guest.post("/api/auth/login", json={"pin": "000000"})
        assert wrong.status_code == 401 and wrong.json()["detail"]["message"] == "PIN이 올바르지 않습니다."
    locked = guest.post("/api/auth/login", json={"pin": "000000"})
    assert locked.status_code == 429 and int(locked.headers["retry-after"]) > 0
    # 잠긴 동안에는 맞는 PIN도 받지 않는다
    assert guest.post("/api/auth/login", json={"pin": TEST_PIN}).status_code == 429


def test_login_without_configured_pin_explains_setup(settings):
    with TestClient(create_app(replace(settings, owner_pin_hash=""))) as client:
        session = client.get("/api/auth/session").json()
        assert session["configured"] is False
        response = client.post("/api/auth/login", json={"pin": TEST_PIN})
        assert response.status_code == 401 and "setup_owner.py" in response.json()["detail"]["message"]


def test_owner_file_is_used_when_env_hash_is_empty(settings):
    settings = replace(settings, owner_pin_hash="")
    settings.owner_file.write_text(json.dumps({"pinHash": hash_pin("246802")}), encoding="utf-8")
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/auth/login", json={"pin": "246802"}).status_code == 200


def test_guest_can_read_but_not_mutate(client, guest):
    project_id = create_project(client)
    client.post(f"/api/projects/{project_id}/messages", json={"text": "보고서"})
    reference = client.post(f"/api/projects/{project_id}/references",
                            data={"source": "url", "url": "https://example.org/a"}).json()

    # 읽기·다운로드 경로는 허용
    assert guest.get("/api/projects").status_code == 200
    assert guest.get(f"/api/projects/{project_id}/workspace").status_code == 200
    assert guest.get(f"/api/projects/{project_id}/artifacts").status_code == 200
    assert guest.get("/api/settings/agents").status_code == 200
    assert guest.get("/api/system/usage").status_code == 200

    # 바꾸는 요청은 모두 401
    loid = {"provider": "anthropic", "modelId": "claude-opus-5", "reasoningLevel": "high"}
    mutations = [
        ("post", "/api/projects", {"json": {"name": "x", "mode": "auto"}}),
        ("delete", f"/api/projects/{project_id}", {}),
        ("post", f"/api/projects/{project_id}/messages", {"json": {"text": "지시"}}),
        ("post", f"/api/projects/{project_id}/runs", {}),
        ("post", f"/api/projects/{project_id}/runs/current/stop", {}),
        ("post", f"/api/projects/{project_id}/inputs/whatever/response", {"json": {"answer": "네"}}),
        ("post", f"/api/projects/{project_id}/references", {"data": {"source": "text", "text": "메모"}}),
        ("delete", f"/api/projects/{project_id}/references/{reference['id']}", {}),
        ("patch", "/api/settings/agents/loid", {"json": loid}),
        ("delete", "/api/settings/agents/loid", {}),
        ("patch", "/api/auth/profile", {"data": {"nickname": "해커"}}),
        ("post", "/api/auth/pin", {"json": {"currentPin": TEST_PIN, "newPin": "111111"}}),
    ]
    for method, path, kwargs in mutations:
        response = getattr(guest, method)(path, **kwargs)
        assert response.status_code == 401, (method, path, response.text)
        assert response.json()["detail"]["code"] == "auth_required"
    # 아무것도 바뀌지 않았다
    assert len(client.get("/api/projects").json()) == 1
    assert all(not row["overridden"] for row in client.get("/api/settings/agents").json())


def test_owner_request_from_unknown_origin_is_refused(client):
    response = client.post("/api/projects", json={"name": "x", "mode": "auto"},
                           headers={"Origin": "http://localhost:5555"})
    assert response.status_code == 403
    allowed = client.post("/api/projects", json={"name": "x", "mode": "auto"},
                          headers={"Origin": "http://localhost:3000"})
    assert allowed.status_code == 201


def test_profile_update_with_avatar(client):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    response = client.patch("/api/auth/profile", data={"nickname": "정현"},
                            files={"avatar": ("me.png", png, "image/png")})
    assert response.status_code == 200, response.text
    assert response.json()["profile"] == {"nickname": "정현", "hasAvatar": True,
                                          "updatedAt": response.json()["profile"]["updatedAt"]}
    assert client.get("/api/auth/avatar").content == png

    fake = client.patch("/api/auth/profile", files={"avatar": ("x.png", b"not an image", "image/png")})
    assert fake.status_code == 400
    too_long = client.patch("/api/auth/profile", data={"nickname": "가" * 31})
    assert too_long.status_code == 400


def test_change_pin_logs_everyone_out(settings):
    settings = replace(settings, owner_pin_hash="")
    settings.owner_file.write_text(json.dumps({"pinHash": hash_pin(TEST_PIN)}), encoding="utf-8")
    with TestClient(create_app(settings)) as client:
        login(client)
        wrong = client.post("/api/auth/pin", json={"currentPin": "000000", "newPin": "112233"})
        assert wrong.status_code == 400
        assert client.post("/api/auth/pin", json={"currentPin": TEST_PIN, "newPin": "112233"}).status_code == 200
        assert client.get("/api/auth/session").json()["authenticated"] is False
        assert "112233" not in settings.owner_file.read_text(encoding="utf-8")
        assert client.post("/api/auth/login", json={"pin": "112233"}).status_code == 200


def test_no_owner_secret_is_tracked_in_git():
    """PIN 해시·owner.json이 Git에 올라가지 않는다(.data/는 무시 목록)."""
    tracked = subprocess.run(["git", "ls-files"], cwd=WEBAPP, capture_output=True, text=True, check=True).stdout
    assert "owner.json" not in tracked
    assert "scrypt$" not in (WEBAPP / ".env.example").read_text(encoding="utf-8")
    ignored = subprocess.run(["git", "check-ignore", ".data/owner.json"], cwd=WEBAPP, capture_output=True, text=True)
    assert ignored.returncode == 0
