import json

import pytest

from scripts.quality_gate import (
    QualityGateError,
    count_tests,
    evaluate,
    parse_decision,
    parse_min_coverage,
    read_coverage,
    request_groq,
    write_summary,
)


def test_coverage_below_threshold_blocks_without_api_call(monkeypatch):
    monkeypatch.setattr(
        "scripts.quality_gate.request_groq",
        lambda *args, **kwargs: pytest.fail("API chamada"),
    )
    result = evaluate(69.99, 70, "secret", 4, {})
    assert not result.approved
    assert result.decision == "BLOQUEADO"


def test_coverage_equal_threshold_calls_gate(monkeypatch):
    monkeypatch.setattr(
        "scripts.quality_gate.request_groq", lambda *args, **kwargs: "APROVADO — ok"
    )
    assert evaluate(70, 70, "secret", 4, {}).approved


def test_coverage_above_threshold_can_be_blocked_by_ai(monkeypatch):
    monkeypatch.setattr(
        "scripts.quality_gate.request_groq", lambda *args, **kwargs: "BLOQUEADO — risco"
    )
    assert evaluate(91, 70, "secret", 4, {}).decision == "BLOQUEADO"


@pytest.mark.parametrize(
    "text, expected", [("APROVADO - bom", "APROVADO"), ("BLOQUEADO: revise", "BLOQUEADO")]
)
def test_parse_decision(text, expected):
    assert parse_decision(text) == expected


def test_parse_decision_rejects_missing_or_ambiguous_decision():
    with pytest.raises(QualityGateError):
        parse_decision("resultado inconclusivo")
    with pytest.raises(QualityGateError):
        parse_decision("APROVADO, mas BLOQUEADO se houver risco")


def test_missing_api_key_blocks():
    result = evaluate(80, 70, None, None, {})
    assert result.decision == "BLOQUEADO"
    assert "GROQ_API_KEY" in result.reason


def test_empty_optional_coverage_setting_uses_default():
    assert parse_min_coverage("") == 70


def test_read_coverage_and_count_tests(tmp_path):
    coverage_file = tmp_path / "coverage.json"
    coverage_file.write_text(json.dumps({"totals": {"percent_covered": 72.5}}), encoding="utf-8")
    junit_file = tmp_path / "results.xml"
    junit_file.write_text("<testsuite><testcase/><testcase/></testsuite>", encoding="utf-8")
    assert read_coverage(coverage_file) == 72.5
    assert count_tests(junit_file) == 2


def test_request_groq_http_timeout_and_invalid_json(monkeypatch):
    import urllib.error

    def http_error(*args, **kwargs):
        raise urllib.error.HTTPError("url", 503, "down", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", http_error)
    with pytest.raises(QualityGateError, match="HTTP 503"):
        request_groq("secret", "prompt")

    def timeout(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr("urllib.request.urlopen", timeout)
    with pytest.raises(QualityGateError, match="indisponível"):
        request_groq("secret", "prompt")

    def invalid_json(*args, **kwargs):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"not json"

        return Response()

    monkeypatch.setattr("urllib.request.urlopen", invalid_json)
    with pytest.raises(QualityGateError, match="JSON inválido"):
        request_groq("secret", "prompt")


def test_request_groq_sends_user_agent(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"choices": [{"message": {"content": "APROVADO"}}]}'

    def urlopen(request, timeout):
        assert request.get_header("User-agent") == "financial-market-dashboard/1.0"
        assert request.get_header("Authorization") == "Bearer secret"
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    assert request_groq("secret", "prompt") == "APROVADO"


def test_summary_does_not_include_secret(tmp_path):
    summary = tmp_path / "summary.md"
    result = evaluate(80, 70, None, 2, {})
    write_summary(result, summary)
    contents = summary.read_text(encoding="utf-8")
    assert "GROQ_API_KEY" in contents
    assert "secret" not in contents
