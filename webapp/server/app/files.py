"""FileStore — 파일 시스템이 원본(Source of Truth)이다. DB에는 경로·크기·해시만 둔다.

- 경로는 저장소 루트 기준 상대경로(`/` 구분)로 저장한다.
- 허용한 폴더(작업/ · 최종/ · 자료/ · webapp/.data/) 밖은 읽지도 쓰지도 않는다.
- 사용자가 준 파일명은 그대로 경로에 쓰지 않는다 — 안전한 이름을 새로 만든다.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import BinaryIO

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
_CHUNK = 1024 * 1024
ALLOWED_TOP_DIRS = ("작업", "최종", "자료")

_FILE_TYPE_BY_EXT = {
    ".md": "markdown", ".txt": "markdown",
    ".pdf": "pdf",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".webp": "image", ".svg": "image",
    ".pptx": "pptx",
}
_REFERENCE_KIND_BY_EXT = {".pdf": "pdf", ".md": "markdown", ".txt": "text",
                          ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".webp": "image"}

mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx")


class UnsafePathError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


def sanitize_filename(name: str, fallback: str = "file") -> str:
    """경로 구분자·제어문자·예약문자를 없앤 파일명. 한글은 그대로 둔다."""
    name = unicodedata.normalize("NFC", PurePosixPath(name.replace("\\", "/")).name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = re.sub(r"\s+", "_", stem)[:100] or fallback
    ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:10]
    safe = f"{stem}.{ext}" if ext else stem
    # Windows 예약 이름(CON, NUL 등)
    if re.fullmatch(r"(?i)(con|prn|aux|nul|com\d|lpt\d)", stem):
        safe = f"_{safe}"
    return safe


def mime_type_of(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def file_type_of(path: Path) -> str:
    return _FILE_TYPE_BY_EXT.get(path.suffix.lower(), "file")


def reference_kind_of(name: str) -> str:
    return _REFERENCE_KIND_BY_EXT.get(Path(name).suffix.lower(), "file")


class FileStore:
    def __init__(self, repo_root: Path, data_dir: Path):
        self.repo_root = repo_root.resolve()
        self.data_dir = data_dir.resolve()

    # --- 경로 ----------------------------------------------------------------

    def to_relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.repo_root).as_posix()

    def resolve(self, relative_path: str) -> Path:
        """저장소 루트 기준 상대경로 → 절대경로. 허용 폴더 밖이면 UnsafePathError."""
        if not relative_path or Path(relative_path).is_absolute() or "\\" in relative_path:
            raise UnsafePathError(relative_path)
        path = (self.repo_root / relative_path).resolve()
        self.ensure_allowed(path)
        return path

    def ensure_allowed(self, path: Path) -> Path:
        path = path.resolve()
        allowed = [self.data_dir, *(self.repo_root / top for top in ALLOWED_TOP_DIRS)]
        if not any(path == root or path.is_relative_to(root) for root in allowed):
            raise UnsafePathError(str(path))
        # 허용 폴더 안이라도 결국 저장소 밖(예: 심볼릭 링크)이면 거절
        if not path.is_relative_to(self.repo_root):
            raise UnsafePathError(str(path))
        return path

    # --- 저장 ----------------------------------------------------------------

    def unique_path(self, directory: Path, safe_name: str) -> Path:
        directory = self.ensure_allowed(directory)
        directory.mkdir(parents=True, exist_ok=True)
        candidate = directory / safe_name
        stem, suffix = candidate.stem, candidate.suffix
        counter = 2
        while candidate.exists():
            candidate = directory / f"{stem}_{counter}{suffix}"
            counter += 1
        return self.ensure_allowed(candidate)

    def save_stream(self, directory: Path, original_name: str, stream: BinaryIO) -> tuple[Path, int, str]:
        """업로드 저장. (저장 경로, 크기, sha256). 한도를 넘으면 쓰던 파일을 지운다."""
        target = self.unique_path(directory, sanitize_filename(original_name))
        digest, size = hashlib.sha256(), 0
        try:
            with target.open("wb") as out:
                while chunk := stream.read(_CHUNK):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise UploadTooLargeError(original_name)
                    digest.update(chunk)
                    out.write(chunk)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target, size, digest.hexdigest()

    def save_text(self, directory: Path, title: str, text: str) -> tuple[Path, int, str]:
        target = self.unique_path(directory, sanitize_filename(f"{title}.md", fallback="text"))
        data = text.encode("utf-8")
        target.write_bytes(data)
        return target, len(data), hashlib.sha256(data).hexdigest()
