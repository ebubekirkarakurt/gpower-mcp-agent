"""Shared helpers for MCP tests: call the power_analysis tool through a real MCP client."""

import json
from typing import Any, Dict, List, Tuple

import anyio
from mcp import Client

from gpower_clone.cli import main
from gpower_clone.mcp_server import TOOL_NAME, create_server


def call_mcp(arguments: Dict[str, Any]) -> Tuple[str, bool]:
    """Call power_analysis via an in-process MCP client. Returns (text, is_error)."""

    async def _call() -> Tuple[str, bool]:
        async with Client(create_server()) as client:
            result = await client.call_tool(TOOL_NAME, arguments)
            assert len(result.content) == 1
            assert result.content[0].type == "text"
            return result.content[0].text, bool(result.is_error)

    return anyio.run(_call)


def list_mcp_tools() -> List[Any]:
    async def _list() -> List[Any]:
        async with Client(create_server()) as client:
            return (await client.list_tools()).tools

    return anyio.run(_list)


def run_cli(arguments: Dict[str, Any], capsys) -> Tuple[str, int]:
    """Run the CLI with --key value pairs. Returns (stdout line without newline, exit code)."""
    argv: List[str] = []
    for key, value in arguments.items():
        argv.extend([f"--{key}", str(value)])
    exit_code = main(argv)
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert len(lines) == 1, f"CLI must print exactly one line, got: {out!r}"
    return lines[0], exit_code


def parse(text: str) -> Dict[str, Any]:
    return json.loads(text)
