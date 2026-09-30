"""프로젝트 파일을 Git에 반영한다 — 그 프로젝트의 경로만 커밋해 작업트리의 다른 변경과 섞지 않는다.

완료: 작업/<ID>·최종/<유형>/<ID>·최종/_manifest.md를 커밋하고 푸시한다(결과물이 로컬에만 남지 않게).
삭제: 같은 경로를 커밋만 한다 — 실수로 지웠으면 이 커밋을 되돌려 살린다. 푸시는 다음 완료 때 함께 나간다.
실제 저장소(claude 오케스트레이터)에서만 돈다. 끄기: DOCUMASTER_GIT_SYNC=0
"""

from __future__ import annotations

import logging
import re
import subprocess
import threading
from pathlib import Path

from . import scanner
from .config import Settings

log = logging.getLogger(__name__)

MANIFEST = Path("최종") / "_manifest.md"
TIMEOUT_SECONDS = 180  # 커밋 전 훅(.githooks/pre-commit)이 테스트를 돌 수 있다
_LOCK = threading.Lock()  # git 명령은 한 번에 하나씩


class GitSyncError(RuntimeError):
    pass


def enabled(settings: Settings, work_root: Path) -> bool:
    return (settings.git_sync and settings.orchestrator == "claude"
            and work_root.resolve() == settings.repo_root and (settings.repo_root / ".git").exists())


def project_paths(work_root: Path, workspace_id: str) -> list[Path]:
    """이 프로젝트가 저장소에 남기는 경로(저장소 기준 상대 경로). 지우기 전에 불러야 최종 폴더를 찾는다."""
    paths = [Path("작업") / workspace_id]
    paths += [final.relative_to(work_root) for final in scanner.final_dirs(work_root, workspace_id)]
    return paths + [MANIFEST]


def drop_manifest_entry(work_root: Path, workspace_id: str) -> None:
    """최종/_manifest.md에서 이 작업 ID의 줄을 지운다(목록에 지운 프로젝트가 남지 않게)."""
    manifest = work_root / MANIFEST
    if not manifest.is_file():
        return
    lines = manifest.read_text(encoding="utf-8").splitlines(keepends=True)
    marker = re.compile(rf"`{re.escape(workspace_id)}`")
    kept = [line for line in lines if not marker.search(line)]
    if len(kept) != len(lines):
        manifest.write_text("".join(kept), encoding="utf-8")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=repo, capture_output=True, check=False,
                          text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS)


def commit_paths(repo: Path, paths: list[Path], message: str, push: bool) -> bool:
    """paths만 커밋한다(다른 staged 변경은 그대로 둔다). 바뀐 것이 없으면 False."""
    with _LOCK:
        specs = [p.as_posix() for p in paths
                 if (repo / p).exists() or _git(repo, "ls-files", "--", p.as_posix()).stdout.strip()]
        if not specs:
            return False
        done = _git(repo, "add", "-A", "--", *specs)
        if done.returncode != 0:
            raise GitSyncError(done.stderr.strip() or "git add 실패")
        if _git(repo, "diff", "--cached", "--quiet", "--", *specs).returncode == 0:
            return False
        done = _git(repo, "commit", "-m", message, "--", *specs)
        if done.returncode != 0:
            raise GitSyncError((done.stderr or done.stdout).strip()[-400:] or "git commit 실패")
        if push:
            done = _git(repo, "push", "origin", "HEAD")
            if done.returncode != 0:
                raise GitSyncError("커밋은 했지만 푸시하지 못했습니다: " + done.stderr.strip()[-300:])
        return True
