"""Unit tests for the chi2-contingency calculation engine."""

import pytest
from gpower_clone.engine import (
    compute_post_hoc,
    compute_a_priori,
    compute_compromise,
    compute_criterion,
    compute_sensitivity,
    calculate,
)
from gpower_clone.validation import CalculationError, ValidationError


def test_post_hoc_basic():
    res = compute_post_hoc(w=0.3, alpha=0.05, n_total=100, df=5)
    assert abs(res["ncp"] - 9.0) < 1e-12
    assert abs(res["critical_chi2"] - 11.0704977) < 1e-6
    assert abs(res["power"] - 0.6235846) < 1e-6


def test_post_hoc_df1_minimum():
    # df=1 (2x2 table), n=50
    res = compute_post_hoc(w=0.5, alpha=0.05, n_total=50, df=1)
    assert res["ncp"] == 0.25 * 50
    assert res["power"] > 0.05


def test_a_priori_basic():
    res = compute_a_priori(w=0.3, alpha=0.05, power=0.95, df=5)
    assert res["n_total"] == 220
    assert abs(res["ncp"] - 19.8) < 1e-12
    assert abs(res["critical_chi2"] - 11.0704977) < 1e-6
    assert res["actual_power"] >= 0.95
    assert abs(res["actual_power"] - 0.9502155) < 1e-6


def test_a_priori_large_effect_minimum_n():
    # Huge effect size where N=2 satisfies target power
    res = compute_a_priori(w=10.0, alpha=0.05, power=0.95, df=1)
    assert res["n_total"] == 2
    assert res["actual_power"] > 0.95


def test_a_priori_power_monotonicity():
    res1 = compute_a_priori(w=0.3, alpha=0.05, power=0.80, df=5)
    res2 = compute_a_priori(w=0.3, alpha=0.05, power=0.90, df=5)
    res3 = compute_a_priori(w=0.3, alpha=0.05, power=0.95, df=5)
    assert res1["n_total"] < res2["n_total"] < res3["n_total"]


def test_compromise_basic():
    res = compute_compromise(w=0.3, beta_alpha_ratio=1.0, n_total=100, df=5)
    assert abs(res["ncp"] - 9.0) < 1e-12
    assert abs(res["alpha"] - res["beta"]) < 1e-7  # q=1 so alpha == beta
    assert abs(res["power"] - (1.0 - res["beta"])) < 1e-12
    assert abs(res["critical_chi2"] - 7.6804954) < 1e-6


def test_criterion_basic():
    res = compute_criterion(w=0.3, power=0.95, n_total=100, df=5)
    assert abs(res["ncp"] - 9.0) < 1e-12
    assert abs(res["critical_chi2"] - 4.6618452) < 1e-6
    assert abs(res["alpha"] - 0.4585253) < 1e-6


def test_sensitivity_basic():
    res = compute_sensitivity(alpha=0.05, power=0.95, n_total=100, df=5)
    assert abs(res["ncp"] - 19.7801344) < 1e-6
    assert abs(res["critical_chi2"] - 11.0704977) < 1e-6
    assert abs(res["w"] - 0.4447486) < 1e-6


def test_calculate_dispatch():
    params = {
        "test": "chi2-contingency",
        "mode": "post-hoc",
        "w": 0.3,
        "alpha": 0.05,
        "n_total": 100,
        "df": 5,
    }
    res = calculate(params)
    assert "power" in res
    assert abs(res["power"] - 0.6235846) < 1e-6
