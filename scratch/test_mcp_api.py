import asyncio
import json
from mcp.server.mcpserver import MCPServer
from gpower_clone.engine import calculate
from gpower_clone.validation import GPowerError

server = MCPServer("gpower-clone")

@server.tool(name="power_analysis")
def power_analysis(
    test: str,
    mode: str,
    w: float = None,
    alpha: float = None,
    power: float = None,
    df: int = None,
    n_total: int = None,
    beta_alpha_ratio: float = None,
) -> str:
    """Perform statistical power analysis according to CONTRACT.md."""
    raw_params = {"test": test, "mode": mode}
    if w is not None:
        raw_params["w"] = w
    if alpha is not None:
        raw_params["alpha"] = alpha
    if power is not None:
        raw_params["power"] = power
    if df is not None:
        raw_params["df"] = df
    if n_total is not None:
        raw_params["n_total"] = n_total
    if beta_alpha_ratio is not None:
        raw_params["beta_alpha_ratio"] = beta_alpha_ratio

    try:
        res = calculate(raw_params)
        return json.dumps(res, ensure_ascii=False)
    except GPowerError as e:
        return json.dumps(e.to_dict(), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "code": "NO_SOLUTION"}, ensure_ascii=False)

async def test():
    tools = await server.list_tools()
    print("Tools count:", len(tools))
    print("Tool name:", tools[0].name)
    print("Tool schema:", tools[0].inputSchema)
    
    # Test valid call
    res = await server.call_tool("power_analysis", {
        "test": "chi2-contingency",
        "mode": "post-hoc",
        "w": 0.3,
        "alpha": 0.05,
        "n_total": 100,
        "df": 5
    })
    print("\nCall post-hoc result:", res)
    print("Text content:", res[0].content[0].text)
    
    # Test error call (missing n_total)
    res_err = await server.call_tool("power_analysis", {
        "test": "chi2-contingency",
        "mode": "post-hoc",
        "w": 0.3,
        "alpha": 0.05,
        "df": 5
    })
    print("\nCall error result:", res_err[0].content[0].text)

if __name__ == "__main__":
    asyncio.run(test())
