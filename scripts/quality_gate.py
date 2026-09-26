"""Run the project's deterministic and AI-assisted quality gate.

The Groq call intentionally uses only Python's standard library so this script
can run in CI without adding a runtime dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_MIN_COVERAGE = 70.0


class QualityGateError(RuntimeError):
    """An error that must block the quality gate."""


@dataclass(frozen=True)
class GateResult:
    coverage: float
    minimum_coverage: float
    decision: str
    reason: str
    test_count: int | None = None
    model: str | None = None

    @property
    def approved(self) -> bool:
        return self.decision == "APROVADO"


def read_coverage(path: str | Path) -> float:
    """Read the total percentage covered from a coverage.py JSON report."""
    try:
        with Path(path).open(encoding="utf-8") as coverage_file:
            report = json.load(coverage_file)
        value = report["totals"]["percent_covered"]
        return float(value)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise QualityGateError(f"Não foi possível ler a cobertura de {path}") from exc


def parse_min_coverage(value: str | None) -> float:
    """Parse and validate the configured minimum coverage percentage."""
    try:
        minimum = DEFAULT_MIN_COVERAGE if value in (None, "") else float(value)
    except ValueError as exc:
        raise QualityGateError("QUALITY_GATE_MIN_COVERAGE deve ser um número") from exc
    if not 0 <= minimum <= 100:
        raise QualityGateError("QUALITY_GATE_MIN_COVERAGE deve estar entre 0 e 100")
    return minimum


def parse_decision(response_text: str) -> str:
    """Return the sole decision token in an AI response."""
    decisions = set(re.findall(r"\b(APROVADO|BLOQUEADO)\b", response_text.upper()))
    if len(decisions) != 1:
        raise QualityGateError("A resposta da IA não contém uma decisão reconhecível")
    return decisions.pop()


def count_tests(junit_path: str | Path | None) -> int | None:
    """Read the number of testcases from an optional pytest JUnit report."""
    if not junit_path:
        return None
    try:
        root = ET.parse(junit_path).getroot()
    except (OSError, ET.ParseError):
        return None
    return len(root.findall(".//testcase"))


def build_prompt(coverage: float, test_count: int | None, ci_context: dict[str, str]) -> str:
    """Build a small, bounded prompt containing only non-secret CI metadata."""
    tests = str(test_count) if test_count is not None else "não informado"
    event = ci_context.get("GITHUB_EVENT_NAME", "execução local")
    branch = ci_context.get("GITHUB_REF_NAME", "não informado")
    return (
        "Você é um quality gate auxiliar. Responda com APROVADO ou BLOQUEADO "
        "e uma justificativa curta. Não substitua testes, lint ou revisão humana.\n"
        f"Cobertura total: {coverage:.2f}% (mínimo determinístico: "
        f"{ci_context.get('QUALITY_GATE_MIN_COVERAGE', DEFAULT_MIN_COVERAGE)}%).\n"
        f"Quantidade de testes: {tests}.\n"
        f"CI: evento={event}, branch={branch}."
    )


def request_groq(
    api_key: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 30.0,
) -> str:
    """Call Groq's OpenAI-compatible endpoint and return only message content."""
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "Avalie o contexto de CI de forma conservadora e objetiva.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "financial-market-dashboard/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        raise QualityGateError(f"API do Groq indisponível (HTTP {exc.code})") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise QualityGateError("API do Groq indisponível ou expirou o tempo limite") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise QualityGateError("A API do Groq retornou JSON inválido") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise QualityGateError("A resposta da API do Groq tem formato inválido") from exc
    if not isinstance(content, str):
        raise QualityGateError("A resposta da API do Groq tem formato inválido")
    return content


def evaluate(
    coverage: float,
    minimum_coverage: float,
    api_key: str | None,
    test_count: int | None,
    ci_context: dict[str, str],
    model: str = DEFAULT_MODEL,
) -> GateResult:
    """Evaluate coverage first, then ask the AI only when deterministic checks pass."""
    if coverage < minimum_coverage:
        return GateResult(
            coverage,
            minimum_coverage,
            "BLOQUEADO",
            f"cobertura abaixo do mínimo ({minimum_coverage:.2f}%)",
            test_count,
            model,
        )
    if not api_key:
        return GateResult(
            coverage,
            minimum_coverage,
            "BLOQUEADO",
            "GROQ_API_KEY não configurada",
            test_count,
            model,
        )
    response = request_groq(api_key, build_prompt(coverage, test_count, ci_context), model=model)
    decision = parse_decision(response)
    return GateResult(
        coverage,
        minimum_coverage,
        decision,
        "decisão da avaliação de IA",
        test_count,
        model,
    )


def write_summary(result: GateResult, summary_path: str | Path | None) -> None:
    """Write a concise summary without the API key or the raw AI response."""
    if not summary_path:
        return
    status = "✅ APROVADO" if result.approved else "❌ BLOQUEADO"
    tests = str(result.test_count) if result.test_count is not None else "não informado"
    summary = (
        "## Quality gate\n\n"
        f"- Resultado: {status}\n"
        f"- Cobertura: {result.coverage:.2f}% (mínimo: {result.minimum_coverage:.2f}%)\n"
        f"- Testes: {tests}\n"
        f"- Motivo: {result.reason}\n"
    )
    Path(summary_path).write_text(summary, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-file", default="coverage.json")
    parser.add_argument("--junit-file", default="test-results.xml")
    args = parser.parse_args()

    minimum = parse_min_coverage(os.getenv("QUALITY_GATE_MIN_COVERAGE"))
    coverage = read_coverage(args.coverage_file)
    context = dict(os.environ)
    context["QUALITY_GATE_MIN_COVERAGE"] = str(minimum)
    result = evaluate(
        coverage,
        minimum,
        os.getenv("GROQ_API_KEY"),
        count_tests(args.junit_file),
        context,
        model=os.getenv("GROQ_MODEL") or DEFAULT_MODEL,
    )
    write_summary(result, os.getenv("GITHUB_STEP_SUMMARY"))
    print(
        f"Quality gate: {result.decision} — cobertura {result.coverage:.2f}% "
        f"(mínimo {result.minimum_coverage:.2f}%) — {result.reason}"
    )
    return 0 if result.approved else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QualityGateError as exc:
        print(f"Quality gate: BLOQUEADO — {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
