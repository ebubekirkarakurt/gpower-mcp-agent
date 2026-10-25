"""Command Line Interface (CLI) for gpower-clone.

Conforms strictly to CONTRACT.md specification:
- stdout contains ONLY single-line JSON
- exit code 0 on success
- exit code 2 on invalid input / validation error
- exit code 1 on internal calculation error
"""

import json
import sys
from typing import Any, Dict, List

from gpower_clone.engine import calculate
from gpower_clone.validation import GPowerError, ValidationError, CalculationError

CONTRACT_VERSION = "1.0.0"
TEAM_NAME = "gpower-clone"
ENGINE_INFO = f"python {sys.version_info.major}.{sys.version_info.minor}"


def print_json_stdout(data: Dict[str, Any]) -> None:
    """Print dictionary as compact single-line JSON to stdout."""
    # Ensure standard JSON formatting (no NaN, null for none, dot decimal separator)
    json_str = json.dumps(data, ensure_ascii=False)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()


def parse_cli_args(argv: List[str]) -> Dict[str, Any]:
    """Parse key-value pairs from argv list (--key value)."""
    params: Dict[str, Any] = {}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--"):
            key = arg[2:]
            if not key:
                i += 1
                continue
            # Look ahead for value
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                val = argv[i + 1]
                params[key] = val
                i += 2
            else:
                # Key passed without value
                params[key] = ""
                i += 1
        else:
            # Positional argument or unexpected token
            raise ValidationError(
                f"Unexpected token '{arg}'. All arguments must be '--<key> <value>'",
                code="UNKNOWN_PARAM",
                field=arg.lstrip("-"),
            )
    return params


def main(argv: List[str] | None = None) -> int:
    """Main CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    # 1. Version query check
    if "--version" in argv or (len(argv) == 1 and argv[0] == "-v"):
        version_payload = {
            "contract_version": CONTRACT_VERSION,
            "name": TEAM_NAME,
            "engine": ENGINE_INFO,
        }
        print_json_stdout(version_payload)
        return 0

    try:
        # 2. Parse arguments
        raw_params = parse_cli_args(argv)

        # 3. Calculate (performs validation and execution in unified engine)
        result = calculate(raw_params)

        # 4. Print single-line JSON result
        print_json_stdout(result)
        return 0

    except GPowerError as e:
        print_json_stdout(e.to_dict())
        return e.exit_code

    except Exception as e:
        error_payload = {
            "error": f"Internal execution error: {e}",
            "code": "NO_SOLUTION",
        }
        print_json_stdout(error_payload)
        return 1


if __name__ == "__main__":
    sys.exit(main())
