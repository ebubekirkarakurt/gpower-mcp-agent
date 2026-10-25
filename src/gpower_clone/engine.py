"""Statistical calculation engine for chi2-contingency tests.

Implements clean-room mathematical methods using SciPy chi2 and ncx2 distributions.
Provides calculation routines for all 5 power analysis modes:
- post-hoc
- a-priori
- compromise
- criterion
- sensitivity
"""

import math
from typing import Any, Dict
from scipy.optimize import brentq
from scipy.stats import chi2, ncx2

from gpower_clone.validation import CalculationError, validate_input


def compute_post_hoc(w: float, alpha: float, n_total: int, df: int) -> Dict[str, Any]:
    """Compute achieved power given effect size w, alpha, N, df."""
    try:
        ncp = float(w * w * n_total)
        critical_chi2 = float(chi2.ppf(1.0 - alpha, df))
        power = float(ncx2.sf(critical_chi2, df, ncp))
        return {
            "ncp": ncp,
            "critical_chi2": critical_chi2,
            "power": power,
        }
    except Exception as e:
        raise CalculationError(f"Post-hoc calculation error: {e}")


def compute_a_priori(w: float, alpha: float, power: float, df: int) -> Dict[str, Any]:
    """Compute required sample size N such that achieved power >= target power."""
    try:
        critical_chi2 = float(chi2.ppf(1.0 - alpha, df))

        # Check if minimum sample size N=2 already satisfies target power
        if float(ncx2.sf(critical_chi2, df, w * w * 2)) >= power:
            n_found = 2
        else:
            # Find an upper bracket by exponential search
            low = 2
            high = 4
            while float(ncx2.sf(critical_chi2, df, w * w * high)) < power:
                high *= 2
                if high > 10_000_000:
                    raise CalculationError("Required sample size exceeds realistic bound (>10M)", "NO_SOLUTION")

            # Binary search to find the minimal integer N where power(N) >= target power
            while low < high:
                mid = (low + high) // 2
                if float(ncx2.sf(critical_chi2, df, w * w * mid)) >= power:
                    high = mid
                else:
                    low = mid + 1
            n_found = low

        ncp = float(w * w * n_found)
        actual_power = float(ncx2.sf(critical_chi2, df, ncp))
        return {
            "ncp": ncp,
            "critical_chi2": critical_chi2,
            "n_total": int(n_found),
            "actual_power": actual_power,
        }
    except CalculationError:
        raise
    except Exception as e:
        raise CalculationError(f"A-priori calculation error: {e}")


def compute_compromise(w: float, beta_alpha_ratio: float, n_total: int, df: int) -> Dict[str, Any]:
    """Compute implied alpha and power given beta/alpha ratio."""
    try:
        ncp = float(w * w * n_total)
        q = float(beta_alpha_ratio)

        # f(x) = beta(x) - q * alpha(x) = 0
        def objective(x: float) -> float:
            beta_val = float(ncx2.cdf(x, df, ncp))
            alpha_val = float(chi2.sf(x, df))
            return beta_val - q * alpha_val

        # At x near 0: beta ~ 0, alpha ~ 1 => f ~ -q < 0
        x_low = 1e-12
        # Find upper bracket where f(x) > 0
        x_high = max(float(df), float(ncp)) + 5.0 * math.sqrt(2.0 * df + 4.0 * ncp) + 10.0
        while objective(x_high) <= 0.0:
            x_high *= 2.0
            if x_high > 1e9:
                raise CalculationError("Could not bracket compromise root", "NO_SOLUTION")

        critical_chi2 = float(brentq(objective, x_low, x_high, xtol=1e-12, rtol=1e-12))
        alpha = float(chi2.sf(critical_chi2, df))
        beta = float(q * alpha)
        achieved_power = float(1.0 - beta)

        return {
            "ncp": ncp,
            "critical_chi2": critical_chi2,
            "alpha": alpha,
            "beta": beta,
            "power": achieved_power,
        }
    except CalculationError:
        raise
    except Exception as e:
        raise CalculationError(f"Compromise calculation error: {e}")


def compute_criterion(w: float, power: float, n_total: int, df: int) -> Dict[str, Any]:
    """Compute required alpha given target power."""
    try:
        ncp = float(w * w * n_total)
        beta_target = float(1.0 - power)

        critical_chi2 = float(ncx2.ppf(beta_target, df, ncp))
        alpha = float(chi2.sf(critical_chi2, df))

        return {
            "ncp": ncp,
            "critical_chi2": critical_chi2,
            "alpha": alpha,
        }
    except Exception as e:
        raise CalculationError(f"Criterion calculation error: {e}")


def compute_sensitivity(alpha: float, power: float, n_total: int, df: int) -> Dict[str, Any]:
    """Compute required effect size w given alpha, power, N, df."""
    try:
        critical_chi2 = float(chi2.ppf(1.0 - alpha, df))

        def objective(lam: float) -> float:
            return float(ncx2.sf(critical_chi2, df, lam)) - power

        # Find upper bracket for lambda
        lam_high = 20.0
        while objective(lam_high) <= 0.0:
            lam_high *= 2.0
            if lam_high > 1e9:
                raise CalculationError("Could not bracket sensitivity root", "NO_SOLUTION")

        ncp = float(brentq(objective, 0.0, lam_high, xtol=1e-12, rtol=1e-12))
        w = float(math.sqrt(ncp / n_total))

        return {
            "ncp": ncp,
            "critical_chi2": critical_chi2,
            "w": w,
        }
    except CalculationError:
        raise
    except Exception as e:
        raise CalculationError(f"Sensitivity calculation error: {e}")


def calculate(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """Unified entry point for power calculations.

    Validates input parameters according to CONTRACT.md and dispatches
    to the appropriate mode calculation function.
    """
    params = validate_input(raw_params)
    mode = params["mode"]

    if mode == "post-hoc":
        return compute_post_hoc(
            w=params["w"],
            alpha=params["alpha"],
            n_total=params["n_total"],
            df=params["df"],
        )
    elif mode == "a-priori":
        return compute_a_priori(
            w=params["w"],
            alpha=params["alpha"],
            power=params["power"],
            df=params["df"],
        )
    elif mode == "compromise":
        return compute_compromise(
            w=params["w"],
            beta_alpha_ratio=params["beta_alpha_ratio"],
            n_total=params["n_total"],
            df=params["df"],
        )
    elif mode == "criterion":
        return compute_criterion(
            w=params["w"],
            power=params["power"],
            n_total=params["n_total"],
            df=params["df"],
        )
    elif mode == "sensitivity":
        return compute_sensitivity(
            alpha=params["alpha"],
            power=params["power"],
            n_total=params["n_total"],
            df=params["df"],
        )
    else:
        raise CalculationError(f"Unsupported mode '{mode}'", "UNSUPPORTED")
