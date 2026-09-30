"""git_sync — 그 프로젝트 경로만 커밋하고, 가짜 오케스트레이터·끈 설정에서는 돌지 않는다. 임시 저장소만 쓴다."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from app import git_sync


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=repo, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "작업" / "A_20261001" / "workspace").mkdir(parents=True)
    (root / "최종" / "안내절차" / "A_20261001").mkdir(parents=True)
    (root / "작업" / "A_20261001" / "workspace" / "07_final_document.md").write_text("본문", encoding="utf-8")
    (root / "최종" / "안내절차" / "A_20261001" / "A_20261001.pdf").write_bytes(b"%PDF")
    (root / "최종" / "_manifest.md").write_text(
        "- 2026-10-01 · [안내절차] `A_20261001` · A_20261001.pdf\n- 2026-09-30 · [분석] `B_20260930` · B.pdf\n",
        encoding="utf-8")
    (root / "other.md").write_text("원본", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "test")
    git(root, "config", "core.hooksPath", "/dev/null")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")
    return root


def test_commit_only_touches_project_paths(repo: Path):
    (repo / "other.md").write_text("작업 중인 다른 변경", encoding="utf-8")
    git(repo, "add", "other.md")  # 다른 변경이 staged여도 섞이지 않아야 한다
    (repo / "작업" / "A_20261001" / "workspace" / "07_final_document_v02.md").write_text("v02", encoding="utf-8")
    (repo / "최종" / "안내절차" / "A_20261001" / "A_20261001.pdf").write_bytes(b"%PDF v02")

    paths = git_sync.project_paths(repo, "A_20261001")
    assert git_sync.commit_paths(repo, paths, "docs(final): A 완료", push=False)

    changed = git(repo, "show", "--name-only", "--format=", "HEAD").split()
    assert "작업/A_20261001/workspace/07_final_document_v02.md" in changed
    assert "최종/안내절차/A_20261001/A_20261001.pdf" in changed
    assert "other.md" not in changed
    assert "M  other.md" in git(repo, "status", "--short")  # 여전히 staged로 남아 있다


def test_deletion_commits_removal_and_manifest_line(repo: Path):
    paths = git_sync.project_paths(repo, "A_20261001")  # 지우기 전에 경로를 모은다
    for target in ("작업/A_20261001", "최종/안내절차/A_20261001"):
        shutil.rmtree(repo / target)
    git_sync.drop_manifest_entry(repo, "A_20261001")

    assert git_sync.commit_paths(repo, paths, "chore: A 삭제", push=False)
    assert git(repo, "ls-files", "작업", "최종/안내절차").strip() == ""
    manifest = git(repo, "show", "HEAD:최종/_manifest.md")
    assert "A_20261001" not in manifest and "B_20260930" in manifest


def test_nothing_changed_makes_no_commit(repo: Path):
    before = git(repo, "rev-parse", "HEAD")
    assert not git_sync.commit_paths(repo, git_sync.project_paths(repo, "A_20261001"), "x", push=False)
    assert git(repo, "rev-parse", "HEAD") == before


def test_runs_only_on_real_repository(settings, repo: Path):
    real = replace(settings, repo_root=repo.resolve(), orchestrator="claude")
    assert git_sync.enabled(real, repo)
    assert not git_sync.enabled(replace(real, orchestrator="fake"), repo)
    assert not git_sync.enabled(replace(real, git_sync=False), repo)
    assert not git_sync.enabled(real, repo / "webapp" / ".data" / "sandbox")
