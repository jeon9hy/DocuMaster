"""테스트는 임시 저장소 루트와 가짜 오케스트레이터만 쓴다 — 실제 작업/·최종/과 LLM을 건드리지 않는다."""

from __future__ import annotations

import socket
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from app.auth import hash_pin
from app.config import Settings
from app.main import create_app


# 테스트 전용 PIN(실제 PIN이 아니다). 해시는 느리므로 한 번만 만든다.
TEST_PIN = "135790"
TEST_PIN_HASH = hash_pin(TEST_PIN)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    repo = tmp_path / "repo"
    (repo / "webapp" / ".data").mkdir(parents=True)
    return Settings(
        repo_root=repo.resolve(),
        data_dir=(repo / "webapp" / ".data").resolve(),
        orchestrator="fake",
        claude_permission_mode="auto",
        fake_step_seconds=0.1,  # 감시 간격보다 길게 — 단계마다 에이전트 전환을 한 번씩 볼 수 있게
        poll_seconds=0.02,
        cors_origins=("http://localhost:3000",),
        owner_pin_hash=TEST_PIN_HASH,
        codex_usage_live=False,  # 테스트는 실제 Codex 계정을 조회하지 않는다
    )


def login(client) -> None:
    response = client.post("/api/auth/login", json={"pin": TEST_PIN})
    assert response.status_code == 200, response.text


@contextmanager
def owner_client(settings: Settings):
    """Owner로 로그인한 클라이언트(세션 쿠키를 들고 다닌다)."""
    with TestClient(create_app(settings)) as test_client:
        login(test_client)
        yield test_client


@pytest.fixture
def client(settings: Settings):
    with owner_client(settings) as test_client:
        yield test_client


@pytest.fixture
def guest(settings: Settings):
    """로그인하지 않은 클라이언트"""
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def wait_until(predicate, timeout: float = 30.0, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("시간 안에 조건을 만족하지 못했습니다")


def events_of(client, project_id: str) -> list[dict]:
    return client.get(f"/api/projects/{project_id}/workspace").json()["events"]


def types_of(client, project_id: str) -> list[str]:
    return [event["type"] for event in events_of(client, project_id)]


def create_project(client, name: str = "테스트", mode: str = "auto") -> str:
    response = client.post("/api/projects", json={"name": name, "mode": mode})
    assert response.status_code == 201, response.text
    return response.json()["id"]


class LiveServer:
    def __init__(self, settings: Settings):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        config = uvicorn.Config(create_app(settings), host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        wait_until(lambda: self._up())
        return self

    def _up(self) -> bool:
        try:
            return httpx.get(self.url + "/api/system/health", timeout=1).status_code == 200
        except httpx.HTTPError:
            return False

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=10)


@pytest.fixture
def live_server(settings: Settings):
    with LiveServer(settings) as server:
        yield server


@pytest.fixture
def owner_http(live_server):
    """실제 서버에 Owner로 로그인한 httpx 클라이언트"""
    with httpx.Client(base_url=live_server.url) as http:
        login(http)
        yield http


@pytest.fixture
def slow_settings(settings: Settings) -> Settings:
    return replace(settings, fake_step_seconds=0.3)
