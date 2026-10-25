"""Automated verification of official chi2-contingency reference vectors."""

import json
from pathlib import Path
import pytest

from gpower_clone.cli import main
from gpower_clone.engine import calculate

VECTORS_FILE = Path(__file__).parent.parent / "public_vectors_chi2.jsonl"


def load_vectors():
    vectors = []
    with open(VECTORS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                vectors.append(json.loads(line))
    return vectors


VECTORS = load_vectors()


def assert_field_match(actual: float | int, expected: float | int, field_name: str):
    """Check field match against CONTRACT.md Section 6 tolerances.

    Integers: Exact match.
    Floats: Absolute difference <= 1e-6 OR relative difference <= 1e-6.
    """
    if isinstance(expected, int) and not isinstance(expected, bool):
        assert isinstance(actual, int), f"Field '{field_name}' must be integer, got {type(actual)}"
        assert actual == expected, f"Field '{field_name}' integer mismatch: got {actual}, expected {expected}"
    else:
        actual_f = float(actual)
        expected_f = float(expected)
        abs_diff = abs(actual_f - expected_f)
        rel_diff = abs_diff / abs(expected_f) if expected_f != 0.0 else abs_diff
        assert (
            abs_diff <= 1e-6 or rel_diff <= 1e-6
        ), f"Field '{field_name}' float tolerance exceeded: actual={actual_f}, expected={expected_f}, diff={abs_diff}"


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_engine_vector_exact(vector):
    """Test engine calculation directly against expected vector values."""
    input_data = vector["input"]
    expected_data = vector["expected"]

    result = calculate(input_data)

    for field_name, expected_val in expected_data.items():
        assert field_name in result, f"Expected field '{field_name}' missing from engine result"
        assert_field_match(result[field_name], expected_val, field_name)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_cli_vector_execution(vector, capsys):
    """Test CLI interface execution for each reference vector."""
    input_data = vector["input"]
    expected_data = vector["expected"]

    # Build argv list
    argv = []
    for k, v in input_data.items():
        argv.extend([f"--{k}", str(v)])

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    stdout_lines = captured.out.strip().splitlines()
    assert len(stdout_lines) == 1, "CLI must output exactly one single-line JSON to stdout"

    parsed_output = json.loads(stdout_lines[0])
    for field_name, expected_val in expected_data.items():
        assert field_name in parsed_output, f"Field '{field_name}' missing in CLI stdout"
        assert_field_match(parsed_output[field_name], expected_val, field_name)
