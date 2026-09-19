"""경로와 실행 설정. 값은 환경변수로만 바꾼다(테스트는 임시 폴더를 넘긴다)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# webapp/server/app/config.py → 저장소 루트
_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    """fake = 비용 없는 가짜 오케스트레이터(샌드박스에 계약 파일을 씀), claude = 실제 로이드 세션"""
    orchestrator: str
    """claude -p에 넘길 --permission-mode. 기본은 사용자가 CLI에서 쓰는 방식과 같게 둔다(Phase D에서 승인)."""
    claude_permission_mode: str
    """가짜 오케스트레이터 한 단계 사이 대기(초). 테스트는 0에 가깝게."""
    fake_step_seconds: float
    """실행 중 작업 폴더를 다시 보는 간격(초)"""
    poll_seconds: float
    cors_origins: tuple[str, ...]
    """Owner PIN의 해시(scrypt$...). 비어 있으면 data_dir/owner.json을 본다. 원문 PIN은 어디에도 두지 않는다."""
    owner_pin_hash: str = ""
    """HTTPS로 띄울 때만 True — 로컬 http에서 True면 브라우저가 쿠키를 버린다."""
    cookie_secure: bool = False
    """Codex CLI 홈(사용량 기록을 읽기만 한다). 기본 ~/.codex"""
    codex_home: Path | None = None
    """설정 화면의 Codex 사용량을 codex app-server로 실시간 조회할지(테스트는 끈다)"""
    codex_usage_live: bool = True

    @property
    def db_path(self) -> Path:
        return self.data_dir / "documaster.db"

    @property
    def sandbox_root(self) -> Path:
        """fake 모드의 작업/·최종/·자료/가 생기는 곳. 실제 작업/·최종/을 건드리지 않는다."""
        return self.data_dir / "sandbox"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def owner_file(self) -> Path:
        """setup_owner.py가 PIN 해시를 쓰는 곳(.data/는 Git에 올라가지 않는다)."""
        return self.data_dir / "owner.json"

    @property
    def claude_usage_file(self) -> Path:
        """server/claude_statusline.py(Claude Code statusLine)가 쓰는 사용량 캐시"""
        return self.data_dir / "claude_usage.json"

    @property
    def profile_dir(self) -> Path:
        return self.data_dir / "profile"


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("DOCUMASTER_DATA_DIR") or _REPO_ROOT / "webapp" / ".data")
    origins = os.environ.get("DOCUMASTER_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return Settings(
        repo_root=Path(os.environ.get("DOCUMASTER_REPO_ROOT") or _REPO_ROOT).resolve(),
        data_dir=data_dir.resolve(),
        orchestrator=os.environ.get("DOCUMASTER_ORCHESTRATOR", "fake"),
        claude_permission_mode=os.environ.get("DOCUMASTER_CLAUDE_PERMISSION_MODE", "auto"),
        fake_step_seconds=float(os.environ.get("DOCUMASTER_FAKE_STEP_SECONDS", "1.0")),
        poll_seconds=float(os.environ.get("DOCUMASTER_POLL_SECONDS", "1.0")),
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
        owner_pin_hash=os.environ.get("DOCUMASTER_OWNER_PIN_HASH", ""),
        cookie_secure=os.environ.get("DOCUMASTER_COOKIE_SECURE", "") == "1",
        codex_home=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"),
    )
