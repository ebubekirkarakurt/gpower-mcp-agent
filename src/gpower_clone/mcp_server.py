"""MCP server for gpower-clone.

Exposes a single tool, `power_analysis`, as required by CONTRACT.md Section 7:
- input field names are identical to the CLI flags
- output is the same single-line JSON the CLI writes to stdout, returned as text content
- errors return the same error JSON
- no calculation logic lives here; every call goes through engine.calculate()

The low-level Server is used on purpose: the SDK does not validate or coerce the
arguments, so unknown fields, floats for integers etc. reach validate_input() and
produce the contract error codes exactly as the CLI does.
"""

import json
from typing import Any, Dict, Tuple

import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from gpower_clone.engine import calculate
from gpower_clone.validation import GPowerError

TOOL_NAME = "power_analysis"

TOOL_DESCRIPTION = """G*Power 3.1.9.7 davranışını izleyen bağımsız güç analizi motoru (gpower-clone).
Desteklenen test: chi2-contingency (χ² tests – Goodness-of-fit tests: Contingency tables).

Modlara göre ZORUNLU alanlar (başka alan verilirse UNKNOWN_PARAM hatası döner):
- a-priori    (gerekli örneklem büyüklüğü): w, alpha, power, df
- post-hoc    (ulaşılan güç):               w, alpha, n_total, df
- compromise  (β/α oranına göre α ve güç):  w, beta_alpha_ratio, n_total, df
- criterion   (gerekli α):                  w, power, n_total, df
- sensitivity (saptanabilir en küçük w):    alpha, power, n_total, df

Varsayılan değer yoktur. Çıktı, CLI'nin stdout'a yazdığı tek satır JSON'dur.
Hata durumunda {"error": ..., "code": ..., "field": ...} JSON'u döner."""

INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "test": {"type": "string", "description": "Test kimliği: chi2-contingency"},
        "mode": {
            "type": "string",
            "enum": ["a-priori", "post-hoc", "compromise", "criterion", "sensitivity"],
            "description": "Analiz modu",
        },
        "w": {"type": "number", "description": "Effect size w (> 0)"},
        "alpha": {"type": "number", "description": "α err prob (0 < alpha < 1)"},
        "power": {"type": "number", "description": "Power (1-β err prob) (0 < power < 1)"},
        "beta_alpha_ratio": {"type": "number", "description": "β/α ratio (> 0), yalnızca compromise"},
        "n_total": {"type": "integer", "description": "Total sample size (tam sayı, >= 2)"},
        "df": {"type": "integer", "description": "Df, serbestlik derecesi (tam sayı, >= 1); (satır-1)×(sütun-1)"},
    },
    "required": ["test", "mode"],
    # Unknown fields must reach the engine so it can answer UNKNOWN_PARAM like the CLI.
    "additionalProperties": True,
}


def to_json_line(data: Dict[str, Any]) -> str:
    """Serialize exactly as cli.print_json_stdout does (without the trailing newline)."""
    return json.dumps(data, ensure_ascii=False)


def run_power_analysis(arguments: Dict[str, Any] | None) -> Tuple[str, bool]:
    """Run the engine and return (json_text, is_error), mirroring cli.main error handling."""
    try:
        return to_json_line(calculate(dict(arguments or {}))), False
    except GPowerError as e:
        return to_json_line(e.to_dict()), True
    except Exception as e:
        error_payload = {
            "error": f"Internal execution error: {e}",
            "code": "NO_SOLUTION",
        }
        return to_json_line(error_payload), True


async def handle_list_tools(ctx: Any, params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name=TOOL_NAME,
                description=TOOL_DESCRIPTION,
                input_schema=INPUT_SCHEMA,
            )
        ]
    )


async def handle_call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
    if params.name != TOOL_NAME:
        text = to_json_line({"error": f"Unknown tool '{params.name}'", "code": "UNSUPPORTED"})
        return types.CallToolResult(content=[types.TextContent(text=text)], is_error=True)

    text, is_error = run_power_analysis(params.arguments)
    return types.CallToolResult(content=[types.TextContent(text=text)], is_error=is_error)


def create_server() -> Server:
    """Build the MCP server exposing only the power_analysis tool."""
    return Server(
        "gpower-clone",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )


async def serve_stdio() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point: serve the MCP tool over stdio."""
    anyio.run(serve_stdio)


if __name__ == "__main__":
    main()
