"""사용량: 실제로 확인되는 값만, 없거나 오래되면 그렇다고 표시한다."""

import io
import json
import sys

import claude_statusline
from app.usage import claude_usage, codex_usage, codex_usage_from, usage_report

NOW = 1_790_000_000


def statusline_input(five=36.0, week=21.0) -> dict:
    return {"model": {"display_name": "Opus"}, "context_window": {"used_percentage": 12},
            "rate_limits": {"five_hour": {"used_percentage": five, "resets_at": NOW + 3600},
                            "seven_day": {"used_percentage": week, "resets_at": NOW + 86400}}}


def test_statusline_saves_only_rate_limits_atomically(tmp_path):
    cache = tmp_path / "claude_usage.json"
    assert claude_statusline.save(statusline_input(), cache)
    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert saved["source"] == "claude-code-statusline" and saved["captured_at"]
    assert saved["five_hour"]["used_percentage"] == 36.0 and saved["seven_day"]["resets_at"] == NOW + 86400
    assert set(saved) == {"source", "captured_at", "five_hour", "seven_day"}  # 사용량 말고는 남기지 않는다
    assert list(tmp_path.glob(".claude_usage.*")) == []  # 임시 파일이 남지 않는다

    # rate_limits가 없으면(첫 응답 전) 캐시를 건드리지 않는다
    assert not claude_statusline.save({"model": {"display_name": "Opus"}}, cache)
    # 한 창만 오면 그 창만 갱신하고 다른 창은 이전 값 유지
    only_five = statusline_input(five=50.0)
    del only_five["rate_limits"]["seven_day"]
    claude_statusline.save(only_five, cache)
    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert saved["five_hour"]["used_percentage"] == 50.0 and saved["seven_day"]["used_percentage"] == 21.0


def test_statusline_main_always_prints_a_line(tmp_path, monkeypatch, capsysbinary):
    real = claude_statusline.CACHE
    monkeypatch.setattr(claude_statusline, "CACHE", tmp_path / "c.json")
    for raw in (json.dumps(statusline_input()).encode(), b"not json", b""):
        monkeypatch.setattr(sys, "stdin", type("S", (), {"buffer": io.BytesIO(raw)})())
        assert claude_statusline.main() == 0
    out = capsysbinary.readouterr().out.decode("utf-8")
    assert "[Opus] · ctx 12% · 5h 36% · 7d 21%" in out and "[Claude]" in out
    assert (tmp_path / "c.json").exists()
    assert not real.exists() or "1790003600" not in real.read_text(encoding="utf-8")  # 실제 캐시를 건드리지 않았다


def test_claude_usage_reads_cache_and_marks_expired_windows(tmp_path):
    cache = tmp_path / "claude_usage.json"
    assert "아직 받지 못했습니다" in claude_usage(cache, NOW)["note"]
    cache.write_text("{broken", encoding="utf-8")
    broken = claude_usage(cache, NOW)
    assert broken["available"] is False and "손상" in broken["note"]

    claude_statusline.save(statusline_input(), cache)
    fresh = claude_usage(cache, NOW)
    assert fresh["available"] and not fresh["stale"]
    assert [(w["kind"], w["usedPercent"], w["windowMinutes"]) for w in fresh["windows"]] == [
        ("five_hour", 36.0, 300), ("seven_day", 21.0, 10080)]
    later = claude_usage(cache, NOW + 7200)  # 5시간 창의 리셋이 지남
    assert later["stale"] and later["windows"][0]["expired"] and not later["windows"][1]["expired"]


def test_codex_uses_the_codex_limit_not_other_limits():
    response = {
        "rateLimits": {"limitId": "codex", "primary": {"usedPercent": 0, "windowDurationMins": 300, "resetsAt": NOW},
                       "secondary": {"usedPercent": 100, "windowDurationMins": 10080, "resetsAt": NOW + 10},
                       "rateLimitReachedType": "rate_limit_reached", "planType": "plus"},
        "rateLimitsByLimitId": {
            "base_model_inference": {"limitId": "base_model_inference",
                                     "primary": {"usedPercent": 36, "windowDurationMins": 10080, "resetsAt": NOW}},
            "codex": {"limitId": "codex", "primary": {"usedPercent": 0, "windowDurationMins": 300, "resetsAt": NOW},
                      "secondary": {"usedPercent": 100, "windowDurationMins": 10080, "resetsAt": NOW + 10},
                      "rateLimitReachedType": "rate_limit_reached", "planType": "plus"}},
    }
    usage = codex_usage_from(response)
    assert [(w["windowMinutes"], w["usedPercent"]) for w in usage["windows"]] == [(300, 0.0), (10080, 100.0)]
    assert usage["limitReached"] == "rate_limit_reached"


def test_codex_failure_is_reported_not_invented():
    def fail():
        raise RuntimeError("로그인 필요")
    import app.usage as usage_module
    usage_module._codex_cache = None
    result = codex_usage(fail)
    assert result["available"] is False and "로그인 필요" in result["note"]


def test_report_order_and_notebooklm(tmp_path):
    report = usage_report(tmp_path / "none.json", codex_live=False)
    assert [item["provider"] for item in report] == ["anthropic", "openai", "google"]
    assert all(not item["available"] and item["windows"] == [] for item in report)
