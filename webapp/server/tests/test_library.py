"""문서 라이브러리 — 최종본 폴더에서 유형·날짜·원문 요청을 읽는다(임시 저장소만 쓴다)."""

from __future__ import annotations

from pathlib import Path

from .conftest import owner_client


def _work(repo: Path, workspace_id: str, title: str, request: str, kind: str | None, files: list[str]) -> None:
    folder = repo / "작업" / workspace_id
    (folder / "workspace").mkdir(parents=True)
    (folder / "상태.md").write_text(f"# {workspace_id} — {title} · 모드: DOCUMENT\n상태: 완료\n", encoding="utf-8")
    (folder / "workspace" / "00_user_brief.md").write_text(
        f"# User Brief\n- 글 유형: 분석\n- 원문 요청: {request}\n--- 헤더 끝 ---\n", encoding="utf-8")
    if kind is None:
        return
    final = repo / "최종" / kind / workspace_id
    final.mkdir(parents=True)
    for name in files:
        (final / name).write_bytes(b"%PDF-1.4\n")


def test_library_lists_final_documents_newest_first(settings):
    repo = settings.repo_root
    _work(repo, "최저임금_20260920", "최저임금 해설", "최저임금 알려줘", "설명해설",
          ["최저임금_20260920_원고.md", "최저임금_20260920.pdf"])
    _work(repo, "렘_20260918", "렘 소개 발표", "렘 PPT", "발표", ["렘_20260918_슬라이드.pdf"])
    _work(repo, "진행중_20261001", "아직 진행 중", "진행 중인 요청", None, [])

    with owner_client(settings) as client:
        response = client.get("/api/library")
        assert response.status_code == 200, response.text
        documents = response.json()

    assert [d["workspaceId"] for d in documents] == ["최저임금_20260920", "렘_20260918"]  # 최종본 없는 작업은 빠진다
    first, second = documents
    assert first["title"] == "최저임금 해설"
    assert first["kind"] == "설명해설"
    assert first["date"] == "2026-09-20"
    assert first["request"] == "최저임금 알려줘"
    assert first["fileName"] == "최저임금_20260920.pdf"  # 원고(md)보다 PDF를 대표로
    assert first["artifactId"]  # 가져오기 때 작업물로 등록된 파일을 가리킨다
    assert second["mode"] == "presentation"
    assert second["kind"] == "발표"


def test_library_registers_final_moved_into_kind_folder(settings):
    """최종본이 옛 평면 배치(최종/<ID>)에서 유형 폴더로 옮겨져도 열 수 있게 다시 훑는다."""
    repo = settings.repo_root
    _work(repo, "보고서_20260930", "보고서", "요청", None, [])
    flat = repo / "최종" / "보고서_20260930"
    flat.mkdir(parents=True)
    (flat / "보고서_20260930.pdf").write_bytes(b"%PDF-1.4\n")

    with owner_client(settings) as client:
        before = client.get("/api/library").json()[0]
        assert before["kind"] == "미분류" and before["artifactId"]
        moved = repo / "최종" / "분석" / "보고서_20260930"
        moved.parent.mkdir(parents=True)
        flat.rename(moved)
        after = client.get("/api/library").json()[0]

    assert after["kind"] == "분석"
    assert after["artifactId"] and after["artifactId"] != before["artifactId"]
