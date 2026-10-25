"""Unit tests for the CLI interface, argument parsing, error formatting, and exit codes."""

import json
import pytest

from gpower_clone.cli import main


def test_cli_version(capsys):
    exit_code = main(["--version"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["contract_version"] == "1.0.0"
    assert "name" in data
    assert "engine" in data


def test_cli_missing_param(capsys):
    # Missing alpha and df in post-hoc
    argv = ["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--n_total", "100"]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "MISSING_PARAM"
    assert "error" in data


def test_cli_unknown_param_tails(capsys):
    # Passing --tails in chi2-contingency is forbidden
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "0.3",
        "--alpha", "0.05",
        "--n_total", "100",
        "--df", "5",
        "--tails", "1",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "UNKNOWN_PARAM"
    assert data["field"] == "tails"


def test_cli_irrelevant_param_for_mode(capsys):
    # Passing --power in post-hoc is an unknown/irrelevant parameter
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "0.3",
        "--alpha", "0.05",
        "--n_total", "100",
        "--df", "5",
        "--power", "0.95",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "UNKNOWN_PARAM"
    assert data["field"] == "power"


def test_cli_invalid_value_float_df(capsys):
    # df must be an integer, float 2.5 should be rejected
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "0.3",
        "--alpha", "0.05",
        "--n_total", "100",
        "--df", "2.5",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "INVALID_VALUE"
    assert data["field"] == "df"


def test_cli_out_of_range_alpha(capsys):
    # alpha must be strictly between 0 and 1
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "0.3",
        "--alpha", "1.5",
        "--n_total", "100",
        "--df", "5",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "OUT_OF_RANGE"
    assert data["field"] == "alpha"


def test_cli_out_of_range_w(capsys):
    # w must be > 0
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "-0.2",
        "--alpha", "0.05",
        "--n_total", "100",
        "--df", "5",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "OUT_OF_RANGE"
    assert data["field"] == "w"


def test_cli_out_of_range_df_zero(capsys):
    # df must be >= 1
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "0.3",
        "--alpha", "0.05",
        "--n_total", "100",
        "--df", "0",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "OUT_OF_RANGE"
    assert data["field"] == "df"


def test_cli_inconsistent_power_alpha(capsys):
    # power <= alpha in a-priori is inconsistent
    argv = [
        "--test", "chi2-contingency",
        "--mode", "a-priori",
        "--w", "0.3",
        "--alpha", "0.80",
        "--power", "0.20",
        "--df", "5",
    ]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "INCONSISTENT"
    assert data["field"] == "power"


def test_cli_unsupported_test(capsys):
    argv = ["--test", "non-existent-test", "--mode", "post-hoc"]
    exit_code = main(argv)
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["code"] == "UNSUPPORTED"
    assert data["field"] == "test"


def test_cli_success_stdout_format(capsys):
    argv = [
        "--test", "chi2-contingency",
        "--mode", "post-hoc",
        "--w", "0.3",
        "--alpha", "0.05",
        "--n_total", "100",
        "--df", "5",
    ]
    exit_code = main(argv)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.err == "", "stderr must be empty on success"
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert "power" in data
    assert "ncp" in data
    assert "critical_chi2" in data
