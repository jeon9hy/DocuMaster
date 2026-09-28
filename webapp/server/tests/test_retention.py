"""실행 로그 보존 — 끝난 실행의 오래된 로그 한 벌만 지우고, 나머지(DB·smoke·진행 중 실행)는 두는지."""

import os

from app.retention import prune_run_logs

DAY = 86400
NOW = 1_800_000_000


def touch(path, age_days):
    path.write_text("{}", encoding="utf-8")
    os.utime(path, (NOW - age_days * DAY, NOW - age_days * DAY))


def test_prunes_only_old_finished_run_logs(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    for name in ("run_aaa111.jsonl", "run_aaa111_models.json", "run_aaa111_telemetry.jsonl"):
        touch(logs / name, 40)                      # 오래되고 끝난 실행 — 한 벌 통째로 지운다
    touch(logs / "run_bbb222.jsonl", 40)
    touch(logs / "run_bbb222_models.json", 2)       # 한 벌 중 하나라도 최근이면 남긴다
    touch(logs / "run_ccc333.jsonl", 90)            # 응답 대기 중인 실행 — 남긴다
    touch(logs / "notes.txt", 400)                  # 실행 로그가 아닌 파일 — 건드리지 않는다
    touch(tmp_path / "documaster.db", 400)

    removed = prune_run_logs(logs, 30, keep_run_ids={"run_ccc333"}, now=NOW)
    assert sorted(path.name for path in removed) == [
        "run_aaa111.jsonl", "run_aaa111_models.json", "run_aaa111_telemetry.jsonl"]
    assert sorted(path.name for path in logs.iterdir()) == [
        "notes.txt", "run_bbb222.jsonl", "run_bbb222_models.json", "run_ccc333.jsonl"]
    assert (tmp_path / "documaster.db").exists()
    assert prune_run_logs(logs, 0, set(), now=NOW) == []  # 0이면 끈다
