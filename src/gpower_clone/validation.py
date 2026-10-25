"""Input validation and contract compliance for gpower-clone (chi2-contingency)."""

from typing import Any, Dict, Set


class GPowerError(Exception):
    """Base exception for all gpower-clone errors."""

    def __init__(self, message: str, code: str, field: str | None = None, exit_code: int = 2):
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field
        self.exit_code = exit_code

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"error": self.message, "code": self.code}
        if self.field:
            result["field"] = self.field
        return result


class ValidationError(GPowerError):
    """Validation or contract violation error (exit code 2)."""

    def __init__(self, message: str, code: str, field: str | None = None):
        super().__init__(message, code=code, field=field, exit_code=2)


class CalculationError(GPowerError):
    """Calculation or internal solver error (exit code 1)."""

    def __init__(self, message: str, code: str = "NO_SOLUTION", field: str | None = None):
        super().__init__(message, code=code, field=field, exit_code=1)


SUPPORTED_TESTS: Set[str] = {"chi2-contingency"}

MODE_REQUIRED_PARAMS: Dict[str, Set[str]] = {
    "a-priori": {"w", "alpha", "power", "df"},
    "post-hoc": {"w", "alpha", "n_total", "df"},
    "compromise": {"w", "beta_alpha_ratio", "n_total", "df"},
    "criterion": {"w", "power", "n_total", "df"},
    "sensitivity": {"alpha", "power", "n_total", "df"},
}

INTEGER_PARAMS: Set[str] = {"df", "n_total"}
FLOAT_PARAMS: Set[str] = {"w", "alpha", "power", "beta_alpha_ratio"}


def parse_and_validate_int(value: Any, param_name: str) -> int:
    """Validate and parse integer parameters (df, n_total).

    Rejects non-integers, floats (like 5.5 or '5.0'), and non-numeric strings.
    """
    if isinstance(value, bool):
        raise ValidationError(f"{param_name} must be an integer", code="INVALID_VALUE", field=param_name)

    if isinstance(value, int):
        val = value
    elif isinstance(value, float):
        # A float is invalid where an integer is expected according to contract section 2.4
        raise ValidationError(f"{param_name} must be an integer, got float", code="INVALID_VALUE", field=param_name)
    elif isinstance(value, str):
        val_str = value.strip()
        # Must be pure digits or negative sign with digits, cannot contain decimal point
        if "." in val_str or "," in val_str:
            raise ValidationError(f"{param_name} must be an integer, got decimal", code="INVALID_VALUE", field=param_name)
        try:
            val = int(val_str)
        except ValueError:
            raise ValidationError(f"{param_name} must be an integer", code="INVALID_VALUE", field=param_name)
    else:
        raise ValidationError(f"{param_name} must be an integer", code="INVALID_VALUE", field=param_name)

    # Range checks
    if param_name == "df" and val < 1:
        raise ValidationError("df must be >= 1", code="OUT_OF_RANGE", field="df")
    if param_name == "n_total" and val < 2:
        raise ValidationError("n_total must be >= 2", code="OUT_OF_RANGE", field="n_total")

    return val


def parse_and_validate_float(value: Any, param_name: str) -> float:
    """Validate and parse float parameters (w, alpha, power, beta_alpha_ratio)."""
    if isinstance(value, bool):
        raise ValidationError(f"{param_name} must be a number", code="INVALID_VALUE", field=param_name)

    if isinstance(value, (int, float)):
        val = float(value)
    elif isinstance(value, str):
        try:
            val = float(value.strip())
        except ValueError:
            raise ValidationError(f"{param_name} must be a number", code="INVALID_VALUE", field=param_name)
    else:
        raise ValidationError(f"{param_name} must be a number", code="INVALID_VALUE", field=param_name)

    # Range checks
    if param_name in {"alpha", "power"}:
        if not (0.0 < val < 1.0):
            raise ValidationError(f"{param_name} must be strictly between 0 and 1", code="OUT_OF_RANGE", field=param_name)
    elif param_name in {"w", "beta_alpha_ratio"}:
        if val <= 0.0:
            raise ValidationError(f"{param_name} must be strictly positive", code="OUT_OF_RANGE", field=param_name)

    return val


def validate_input(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input parameter dictionary and return typed, cleaned parameters."""
    # 1. Test check
    if "test" not in params:
        raise ValidationError("Missing --test parameter", code="MISSING_PARAM", field="test")
    test_id = str(params["test"]).strip()
    if test_id not in SUPPORTED_TESTS:
        raise ValidationError(f"Unsupported test '{test_id}'. Only 'chi2-contingency' is supported.", code="UNSUPPORTED", field="test")

    # 2. Mode check
    if "mode" not in params:
        raise ValidationError("Missing --mode parameter", code="MISSING_PARAM", field="mode")
    mode_id = str(params["mode"]).strip()
    if mode_id not in MODE_REQUIRED_PARAMS:
        raise ValidationError(f"Unsupported mode '{mode_id}'", code="UNSUPPORTED", field="mode")

    # 3. Parameter names check
    required_params = MODE_REQUIRED_PARAMS[mode_id]
    allowed_params = {"test", "mode"} | required_params

    # Check for unknown or irrelevant parameters
    for key in params:
        if key not in allowed_params:
            raise ValidationError(f"Unknown or irrelevant parameter '--{key}' for mode '{mode_id}'", code="UNKNOWN_PARAM", field=key)

    # Check for missing parameters
    for key in required_params:
        if key not in params or params[key] is None or params[key] == "":
            raise ValidationError(f"Missing required parameter '--{key}' for mode '{mode_id}'", code="MISSING_PARAM", field=key)

    # 4. Type and range parsing
    cleaned: Dict[str, Any] = {"test": test_id, "mode": mode_id}
    for key in required_params:
        raw_val = params[key]
        if key in INTEGER_PARAMS:
            cleaned[key] = parse_and_validate_int(raw_val, key)
        elif key in FLOAT_PARAMS:
            cleaned[key] = parse_and_validate_float(raw_val, key)
        else:
            cleaned[key] = raw_val

    # 5. Inconsistency checks
    if mode_id in {"a-priori", "sensitivity"}:
        if "power" in cleaned and "alpha" in cleaned:
            if cleaned["power"] <= cleaned["alpha"]:
                raise ValidationError("Power must be greater than alpha", code="INCONSISTENT", field="power")

    return cleaned
