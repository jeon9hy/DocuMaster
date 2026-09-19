import io

from app.files import FileStore, UnsafePathError, sanitize_filename

from .conftest import create_project, events_of


def test_file_upload_is_stored_on_disk_with_hash(client, settings):
    project_id = create_project(client)
    response = client.post(f"/api/projects/{project_id}/references",
                           data={"source": "file", "applyPolicy": "nextStage"},
                           files={"file": ("../../보고서 원본.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")})
    assert response.status_code == 201, response.text
    reference = response.json()
    assert reference["kind"] == "pdf" and reference["parseStatus"] == "ready"
    stored = list((settings.sandbox_root / "자료" / f"web_{project_id}").iterdir())
    assert [path.name for path in stored] == ["보고서_원본.pdf"]  # 경로 조각은 버리고 안전한 이름만
    assert stored[0].read_bytes() == b"%PDF-1.4 test"
    assert events_of(client, project_id)[-1]["type"] == "reference.added"


def test_url_and_text_references_and_removal(client, settings):
    project_id = create_project(client)
    url = client.post(f"/api/projects/{project_id}/references",
                      data={"source": "url", "url": "https://www.molit.go.kr/x", "title": ""})
    assert url.status_code == 201 and url.json()["name"] == "www.molit.go.kr"
    bad = client.post(f"/api/projects/{project_id}/references", data={"source": "url", "url": "file:///etc/passwd"})
    assert bad.status_code == 400
    text = client.post(f"/api/projects/{project_id}/references",
                       data={"source": "text", "title": "메모", "text": "핵심 포인트"})
    assert text.status_code == 201
    assert client.delete(f"/api/projects/{project_id}/references/{url.json()['id']}").status_code == 204
    types = [event["type"] for event in events_of(client, project_id)]
    assert types == ["reference.added", "reference.added", "reference.removed"]


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..") == "file"
    assert sanitize_filename("a<b>:c?.PDF") == "a_b__c_.PDF"
    assert sanitize_filename("CON.txt") == "_CON.txt"
    assert sanitize_filename("주거 정책\t보고서.md") == "주거_정책_보고서.md"


def test_path_traversal_is_rejected(settings):
    store = FileStore(settings.repo_root, settings.data_dir)
    for bad in ("../outside.txt", "작업/../../outside.txt", "/etc/passwd", "C:/Windows/win.ini", "webapp/src/x.ts"):
        try:
            store.resolve(bad)
        except UnsafePathError:
            continue
        raise AssertionError(f"막히지 않음: {bad}")
    (settings.repo_root / "작업" / "a").mkdir(parents=True)
    assert store.resolve("작업/a") == (settings.repo_root / "작업" / "a").resolve()
