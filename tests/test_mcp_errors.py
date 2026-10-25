"""Error handling of the power_analysis MCP tool with native JSON types (CONTRACT.md 2.4, 7)."""

import pytest

from mcp_helpers import call_mcp, parse

BASE = {"test": "chi2-contingency", "mode": "post-hoc", "w": 0.3, "alpha": 0.05, "n_total": 100, "df": 5}


def without(key):
    return {k: v for k, v in BASE.items() if k != key}


def with_(**changes):
    return {**BASE, **changes}


CASES = [
    # (id, arguments, expected code, expected field)
    ("missing-test", without("test"), "MISSING_PARAM", "test"),
    ("missing-mode", without("mode"), "MISSING_PARAM", "mode"),
    ("missing-n_total", without("n_total"), "MISSING_PARAM", "n_total"),
    ("missing-w", without("w"), "MISSING_PARAM", "w"),
    ("null-alpha", with_(alpha=None), "MISSING_PARAM", "alpha"),
    ("unknown-foo", with_(foo=1), "UNKNOWN_PARAM", "foo"),
    ("unknown-tails", with_(tails=1), "UNKNOWN_PARAM", "tails"),
    ("irrelevant-power", with_(power=0.95), "UNKNOWN_PARAM", "power"),
    ("irrelevant-beta_alpha_ratio", with_(beta_alpha_ratio=1), "UNKNOWN_PARAM", "beta_alpha_ratio"),
    ("float-df", with_(df=2.5), "INVALID_VALUE", "df"),
    ("float-n_total", with_(n_total=100.0), "INVALID_VALUE", "n_total"),
    ("bool-df", with_(df=True), "INVALID_VALUE", "df"),
    ("text-w", with_(w="abc"), "INVALID_VALUE", "w"),
    ("list-alpha", with_(alpha=[0.05]), "INVALID_VALUE", "alpha"),
    ("w-zero", with_(w=0), "OUT_OF_RANGE", "w"),
    ("w-negative", with_(w=-0.3), "OUT_OF_RANGE", "w"),
    ("alpha-zero", with_(alpha=0), "OUT_OF_RANGE", "alpha"),
    ("alpha-one", with_(alpha=1), "OUT_OF_RANGE", "alpha"),
    ("n_total-1", with_(n_total=1), "OUT_OF_RANGE", "n_total"),
    ("df-0", with_(df=0), "OUT_OF_RANGE", "df"),
    (
        "power-le-alpha",
        {"test": "chi2-contingency", "mode": "a-priori", "w": 0.3, "alpha": 0.8, "power": 0.2, "df": 5},
        "INCONSISTENT",
        "power",
    ),
    ("unsupported-test", with_(test="t2-indep"), "UNSUPPORTED", "test"),
    ("unsupported-mode", with_(mode="magic"), "UNSUPPORTED", "mode"),
]


@pytest.mark.parametrize("arguments,code,field", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_mcp_error_codes(arguments, code, field):
    text, is_error = call_mcp(arguments)
    assert is_error
    data = parse(text)
    assert "error" in data
    assert data["code"] == code
    assert data["field"] == field


def test_mcp_empty_arguments():
    text, is_error = call_mcp({})
    assert is_error
    assert parse(text)["code"] == "MISSING_PARAM"


def test_mcp_success_is_single_line_json():
    text, is_error = call_mcp(BASE)
    assert not is_error
    assert "\n" not in text
    assert set(parse(text)) == {"ncp", "critical_chi2", "power"}
