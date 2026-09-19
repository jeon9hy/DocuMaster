"""단일 Owner 인증 — 6자리 PIN + HttpOnly 세션 쿠키.

- PIN 원문은 어디에도 저장하지 않는다. 해시(scrypt)만 환경변수 DOCUMASTER_OWNER_PIN_HASH 또는 .data/owner.json에 둔다.
- 검증은 백엔드에서만 한다. 프론트엔드는 정답을 모른다.
- 연속 실패는 늦추고(지연), 5회면 30초 잠근다.
- 세션 토큰은 쿠키로만 주고 DB에는 sha256만 남긴다(localStorage에 두지 않는다).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import Settings
from .db import Database, now_iso

SESSION_COOKIE = "documaster_session"
SESSION_DAYS = 14
PIN_PATTERN = re.compile(r"^\d{6}$")

MAX_FAILURES = 5
LOCK_SECONDS = 30
FAILURE_DELAY_SECONDS = 0.5

DEFAULT_NICKNAME = "Owner"
AVATAR_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
AVATAR_MAX_BYTES = 5 * 1024 * 1024

# scrypt: 메모리를 많이 쓰는 해시(표준 라이브러리). 6자리 PIN은 경우의 수가 적어 느린 해시가 필수다.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**15, 8, 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024


class AuthError(Exception):
    """로그인 실패. message는 사용자에게 그대로 보여 준다."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_pin(pin: str) -> str:
    if not PIN_PATTERN.match(pin):
        raise ValueError("PIN은 숫자 6자리여야 합니다.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
                            maxmem=_SCRYPT_MAXMEM, dklen=32)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(pin.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                maxmem=_SCRYPT_MAXMEM, dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def write_owner_file(path: Path, pin_hash: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pinHash": pin_hash}), encoding="utf-8")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class _Limiter:
    """연속 실패 횟수와 잠금 시각. 로컬 단일 사용자라 메모리로 충분하다(재시작하면 초기화)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.failures = 0
        self.locked_until = 0.0

    def check(self) -> None:
        with self._lock:
            remaining = self.locked_until - time.monotonic()
        if remaining > 0:
            seconds = int(remaining) + 1
            raise AuthError(f"로그인 시도가 너무 많습니다. {seconds}초 뒤 다시 시도하세요.", retry_after=seconds)

    def fail(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= MAX_FAILURES:
                self.failures = 0
                self.locked_until = time.monotonic() + LOCK_SECONDS

    def succeed(self) -> None:
        with self._lock:
            self.failures = 0
            self.locked_until = 0.0


class AuthService:
    def __init__(self, settings: Settings, db: Database, failure_delay: float = FAILURE_DELAY_SECONDS):
        self._settings = settings
        self._db = db
        self._limiter = _Limiter()
        self._failure_delay = failure_delay

    # --- PIN -------------------------------------------------------------------

    def _pin_hash(self) -> str:
        if self._settings.owner_pin_hash:
            return self._settings.owner_pin_hash
        try:
            return json.loads(self._settings.owner_file.read_text(encoding="utf-8")).get("pinHash", "")
        except (OSError, ValueError):
            return ""

    def configured(self) -> bool:
        return bool(self._pin_hash())

    def pin_managed_by_env(self) -> bool:
        return bool(self._settings.owner_pin_hash)

    def login(self, pin: str) -> str:
        """성공하면 새 세션 토큰(쿠키에 넣을 원문)을 돌려준다."""
        self._limiter.check()
        stored = self._pin_hash()
        if not stored:
            raise AuthError("Owner PIN이 아직 설정되지 않았습니다. webapp/server에서 `python setup_owner.py`를 실행하세요.")
        if not PIN_PATTERN.match(pin or "") or not verify_pin(pin, stored):
            self._limiter.fail()
            time.sleep(self._failure_delay)
            self._limiter.check()  # 이번 실패로 잠겼으면 잠금 문구를 보여 준다
            raise AuthError("PIN이 올바르지 않습니다.")
        self._limiter.succeed()
        return self._create_session()

    def change_pin(self, current: str, new: str) -> None:
        if self.pin_managed_by_env():
            raise AuthError("PIN이 환경변수(DOCUMASTER_OWNER_PIN_HASH)로 설정되어 있어 여기서 바꿀 수 없습니다.")
        self._limiter.check()
        if not verify_pin(current or "", self._pin_hash()):
            self._limiter.fail()
            time.sleep(self._failure_delay)
            raise AuthError("현재 PIN이 올바르지 않습니다.")
        if not PIN_PATTERN.match(new or ""):
            raise AuthError("새 PIN은 숫자 6자리여야 합니다.")
        self._limiter.succeed()
        write_owner_file(self._settings.owner_file, hash_pin(new))
        # 다른 브라우저에 남은 세션은 모두 끊는다
        self._db.execute("DELETE FROM sessions")

    # --- 세션 --------------------------------------------------------------------

    def _create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds").replace("+00:00", "Z")
        self._db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (_token_hash(token), now_iso(), expires))
        return token

    def is_owner(self, token: str | None) -> bool:
        if not token:
            return False
        row = self._db.one("SELECT expires_at FROM sessions WHERE token_hash = ?", (_token_hash(token),))
        if row is None:
            return False
        if row["expires_at"] < datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"):
            self.logout(token)
            return False
        return True

    def logout(self, token: str | None) -> None:
        if token:
            self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

    # --- 프로필 ------------------------------------------------------------------

    def profile(self) -> dict:
        row = self._db.one("SELECT * FROM owner_profile WHERE id = 1")
        if row is None:
            return {"nickname": DEFAULT_NICKNAME, "hasAvatar": False, "updatedAt": None}
        return {"nickname": row["nickname"], "hasAvatar": bool(row["avatar_file"]), "updatedAt": row["updated_at"]}

    def avatar_path(self) -> Path | None:
        row = self._db.one("SELECT avatar_file FROM owner_profile WHERE id = 1")
        if row is None or not row["avatar_file"]:
            return None
        path = self._settings.profile_dir / row["avatar_file"]
        return path if path.is_file() else None

    def update_profile(self, nickname: str | None, avatar: tuple[bytes, str] | None, remove_avatar: bool) -> dict:
        current = self.profile()
        name = current["nickname"] if nickname is None else nickname.strip()
        if not name or len(name) > 30:
            raise AuthError("닉네임은 1~30자로 입력해 주세요.")
        row = self._db.one("SELECT avatar_file FROM owner_profile WHERE id = 1")
        avatar_file = row["avatar_file"] if row else None
        if avatar is not None:
            avatar_file = self._save_avatar(*avatar)
        elif remove_avatar:
            avatar_file = None
        self._db.execute(
            "INSERT INTO owner_profile (id, nickname, avatar_file, updated_at) VALUES (1, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET nickname = excluded.nickname, avatar_file = excluded.avatar_file,"
            " updated_at = excluded.updated_at",
            (name, avatar_file, now_iso()),
        )
        return self.profile()

    def _save_avatar(self, data: bytes, content_type: str) -> str:
        if len(data) > AVATAR_MAX_BYTES:
            raise AuthError("프로필 이미지는 5MB 이하만 올릴 수 있습니다.")
        extension = _image_extension(data)
        if extension is None or AVATAR_TYPES.get(content_type) not in (extension, None):
            raise AuthError("프로필 이미지는 PNG·JPG·WEBP만 올릴 수 있습니다.")
        directory = self._settings.profile_dir
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob("avatar_*"):
            old.unlink(missing_ok=True)
        name = f"avatar_{secrets.token_hex(4)}.{extension}"  # 이름을 바꿔 브라우저 캐시를 피한다
        (directory / name).write_bytes(data)
        return name


def _image_extension(data: bytes) -> str | None:
    """확장자·MIME이 아니라 파일 머리(매직 바이트)로 판별한다."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None
