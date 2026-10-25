"""CLI ↔ MCP equivalence tests (CONTRACT.md Section 7).

For every vector the CLI stdout line and the MCP text content must be identical,
and a non-zero CLI exit code must correspond to is_error on the MCP side.
"""

import json
from pathlib import Path

import pytest

from mcp_helpers import call_mcp, list_mcp_tools, parse, run_cli

ROOT = Path(__file__).parent.parent


def load_contract_vectors():
    """Read the 25 reference vectors from CONTRACT.md Section 9 (read-only)."""
    text = (ROOT / "CONTRACT.md").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.startswith('{"id":')]


def load_jsonl(name):
    with open(ROOT / name, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


CONTRACT_VECTORS = load_contract_vectors()
CHI2_VECTORS = load_jsonl("public_vectors_chi2.jsonl")

# Error inputs whose values are given as strings, i.e. exactly what the CLI receives.
ERROR_INPUTS = {
    "missing-test": {"mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "100", "df": "5"},
    "missing-mode": {"test": "chi2-contingency", "w": "0.3", "alpha": "0.05", "n_total": "100", "df": "5"},
    "missing-df": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "100"},
    "unknown-foo": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "100", "df": "5", "foo": "1"},
    "unknown-tails": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "100", "df": "5", "tails": "1"},
    "irrelevant-power": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "100", "df": "5", "power": "0.95"},
    "decimal-df": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "100", "df": "2.5"},
    "text-w": {"test": "chi2-contingency", "mode": "post-hoc", "w": "abc", "alpha": "0.05", "n_total": "100", "df": "5"},
    "alpha-1.5": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "1.5", "n_total": "100", "df": "5"},
    "n_total-1": {"test": "chi2-contingency", "mode": "post-hoc", "w": "0.3", "alpha": "0.05", "n_total": "1", "df": "5"},
    "power-le-alpha": {"test": "chi2-contingency", "mode": "a-priori", "w": "0.3", "alpha": "0.80", "power": "0.20", "df": "5"},
    "unsupported-test": {"test": "t-paired", "mode": "post-hoc"},
    "unsupported-mode": {"test": "chi2-contingency", "mode": "magic"},
}


def assert_equivalent(arguments, capsys):
    cli_text, exit_code = run_cli(arguments, capsys)
    mcp_text, is_error = call_mcp(arguments)
    assert mcp_text == cli_text
    assert is_error == (exit_code != 0)
    return cli_text, exit_code


def test_contract_has_25_vectors():
    assert len(CONTRACT_VECTORS) == 25


def test_only_power_analysis_tool_is_exposed():
    tools = list_mcp_tools()
    assert [t.name for t in tools] == ["power_analysis"]
    schema = tools[0].input_schema
    assert schema["required"] == ["test", "mode"]
    # Same field names as the CLI flags for this family
    assert {"w", "alpha", "power", "df", "n_total", "beta_alpha_ratio"} <= set(schema["properties"])


@pytest.mark.parametrize("vector", CONTRACT_VECTORS, ids=lambda v: v["id"])
def test_contract_vector_cli_equals_mcp(vector, capsys):
    """All 25 CONTRACT.md vectors: identical output; chi2 succeeds, other families fail identically."""
    text, exit_code = assert_equivalent(vector["input"], capsys)
    if vector["input"]["test"] == "chi2-contingency":
        assert exit_code == 0
        assert set(vector["expected"]) <= set(parse(text))
    else:
        assert exit_code == 2
        assert parse(text)["code"] == "UNSUPPORTED"


@pytest.mark.parametrize("vector", CHI2_VECTORS, ids=lambda v: v["id"])
def test_chi2_vector_cli_equals_mcp(vector, capsys):
    text, exit_code = assert_equivalent(vector["input"], capsys)
    assert exit_code == 0
    assert set(vector["expected"]) <= set(parse(text))


@pytest.mark.parametrize("name", list(ERROR_INPUTS))
def test_error_cli_equals_mcp(name, capsys):
    text, exit_code = assert_equivalent(ERROR_INPUTS[name], capsys)
    assert exit_code == 2
    assert "error" in parse(text)
