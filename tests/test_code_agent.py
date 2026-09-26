"""Behavior tests for the standalone one-file repair agent."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest

from scripts import code_agent


@pytest.fixture
def agent_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(code_agent, "ROOT", tmp_path)
    for name in (
        "ARQUIVOS_CONTEXTO",
        "GROQ_MODEL",
        "MODELO",
        "GROQ_API_KEY",
        "GROQCLOUD_API_KEY",
        "API_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OBJETIVO", "Corrigir cálculo")
    monkeypatch.setenv("ARQUIVO_ALVO", "src/indicator.py")
    monkeypatch.setenv("COMANDO_VERIFICACAO", 'test "$(cat src/indicator.py)" = correto')
    monkeypatch.setenv("MAX_TENTATIVAS", "2")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    (tmp_path / "src").mkdir()
    return tmp_path / "src/indicator.py"


def response(content: str) -> str:
    return f"EXPLICACAO: Ajustei o cálculo.\n<<<ARQUIVO\n{content}\nARQUIVO>>>"


def test_no_change_when_verification_passes(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent_environment.write_text("correto\n")
    monkeypatch.setattr(
        code_agent,
        "request_groq",
        lambda *args: pytest.fail("A API não deveria ser chamada"),
    )

    assert code_agent.main() == 0
    assert (code_agent.ROOT / "output").read_text() == "resultado=nada_a_fazer\n"
    assert not (code_agent.ROOT / "pr_body.md").exists()


def test_successful_repair(agent_environment: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent_environment.write_text("errado\n")
    calls = []

    def answer(*args: str) -> str:
        calls.append(args)
        return response("correto")

    monkeypatch.setattr(code_agent, "request_groq", answer)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")

    assert code_agent.main() == 0
    assert agent_environment.read_text() == "correto\n"
    assert (code_agent.ROOT / "output").read_text() == "resultado=alterado\n"
    assert "+correto" in (code_agent.ROOT / "pr_body.md").read_text()
    assert calls[0][:2] == ("test-key", "test-model")


def test_exhausted_attempts_restore_original(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent_environment.write_text("errado\n")
    replies = iter([response("ainda errado"), response("também errado")])
    monkeypatch.setattr(code_agent, "request_groq", lambda *args: next(replies))

    assert code_agent.main() == 0
    assert agent_environment.read_text() == "errado\n"
    assert (code_agent.ROOT / "output").read_text() == "resultado=falhou\n"
    assert "tentou 2 vezes" in (code_agent.ROOT / "issue_body.md").read_text()


def test_failed_creation_removes_target(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(code_agent, "request_groq", lambda *args: response("incompleto"))
    assert code_agent.main() == 0
    assert not agent_environment.exists()


@pytest.mark.parametrize(
    "reply", ["texto sem marcadores", "EXPLICACAO: vazio\n<<<ARQUIVO\nARQUIVO>>>"]
)
def test_malformed_response_restores_original(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    agent_environment.write_text("errado\n")
    monkeypatch.setattr(code_agent, "request_groq", lambda *args: reply)
    assert code_agent.main() == 0
    assert agent_environment.read_text() == "errado\n"
    assert (code_agent.ROOT / "output").read_text() == "resultado=falhou\n"


@pytest.mark.parametrize(
    "api_reply",
    [{"error": {"message": "limite atingido"}}, {"choices": []}, "bad json"],
)
def test_failed_api_response_becomes_report(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch, api_reply: object
) -> None:
    agent_environment.write_text("errado\n")

    class FakeResponse(io.BytesIO):
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            self.close()

    def urlopen(*_args: object, **_kwargs: object) -> FakeResponse:
        data = api_reply if isinstance(api_reply, str) else json.dumps(api_reply)
        return FakeResponse(data.encode())

    monkeypatch.setattr(code_agent.urllib.request, "urlopen", urlopen)
    assert code_agent.main() == 0
    assert agent_environment.read_text() == "errado\n"
    assert (code_agent.ROOT / "output").read_text() == "resultado=falhou\n"


def test_http_error_is_reported(agent_environment: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent_environment.write_text("errado\n")

    def urlopen(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.HTTPError("https://example.test", 503, "Unavailable", {}, None)

    monkeypatch.setattr(code_agent.urllib.request, "urlopen", urlopen)
    assert code_agent.main() == 0
    assert agent_environment.read_text() == "errado\n"


@pytest.mark.parametrize(
    "candidate",
    ["os.system('echo teste')", "linha única"],
)
def test_unsafe_replacement_is_rejected(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch, candidate: str
) -> None:
    original = "errado\nlinha dois\nlinha três\nlinha quatro\n"
    agent_environment.write_text(original)
    monkeypatch.setattr(code_agent, "request_groq", lambda *args: response(candidate))

    assert code_agent.main() == 0
    assert agent_environment.read_text() == original
    assert (code_agent.ROOT / "output").read_text() == "resultado=falhou\n"


@pytest.mark.parametrize(
    "name",
    [
        "../outside.py",
        ".github/workflows/ci.yml",
        "scripts/quality_gate.py",
        ".env",
        "keys.pem",
        "data/secret/file.py",
    ],
)
def test_protected_paths_are_rejected(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv("ARQUIVO_ALVO", name)
    with pytest.raises(code_agent.AgentError, match="não pode alterar"):
        code_agent.main()
    assert not (code_agent.ROOT / "output").exists()


def test_symlink_escape_is_rejected(
    agent_environment: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    outside = tmp_path.parent / "outside-agent.py"
    agent_environment.symlink_to(outside)
    with pytest.raises(code_agent.AgentError, match="não pode alterar"):
        code_agent.main()
