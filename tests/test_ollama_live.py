"""Live end-to-end test with a real local Ollama model and the real MCP server (stdio subprocess).

Skipped (not passed) when the Ollama server is unreachable or the model is not pulled.
Model: GPOWER_OLLAMA_MODEL (default qwen2.5:7b); host: OLLAMA_HOST (default http://localhost:11434).
"""

import json
import os

import anyio
import httpx2
import pytest
from mcp import Client

from gpower_clone.agent import CallLogger, mcp_server_parameters
from gpower_clone.ollama_agent import DEFAULT_OLLAMA_MODEL, OllamaChat, OllamaPowerAnalysisAgent, normalize_host

MODEL = os.environ.get("GPOWER_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
HOST = normalize_host(os.environ.get("OLLAMA_HOST"))
QUESTION = (
    "Kurgusal bir araştırma senaryosu: kontenjans tablosu için ki-kare testi planlıyoruz. "
    "Etki büyüklüğü w=0.3, alpha=0.05, power=0.95 ve df=5. Gerekli toplam örneklem büyüklüğü nedir?"
)


def ollama_model_available() -> str | None:
    """None if usable, otherwise the skip reason."""
    try:
        response = httpx2.get(f"{HOST}/api/tags", timeout=3)
    except httpx2.HTTPError:
        return f"Ollama sunucusuna ulaşılamadı ({HOST})"
    names = {m.get("name") for m in response.json().get("models", [])}
    if MODEL not in names and f"{MODEL}:latest" not in names:
        return f"Ollama modeli indirilmemiş: {MODEL} (ollama pull {MODEL})"
    return None


SKIP_REASON = ollama_model_available()


@pytest.mark.skipif(SKIP_REASON is not None, reason=SKIP_REASON or "")
def test_live_ollama_agent_answers_220(tmp_path):
    log_path = tmp_path / "agent_calls.jsonl"

    async def _run():
        async with Client(mcp_server_parameters()) as mcp_client:
            tools = (await mcp_client.list_tools()).tools
            agent = OllamaPowerAnalysisAgent(OllamaChat(model=MODEL, host=HOST), mcp_client, tools, CallLogger(log_path))
            return await agent.ask(QUESTION)

    answer = anyio.run(_run)
    print(answer)

    assert log_path.exists(), "model did not make a structured MCP tool call"
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    a_priori = [r for r in records if r["tool_input"].get("mode") == "a-priori"]
    assert a_priori, f"no a-priori call in log: {records}"
    rec = a_priori[-1]
    tool_input = rec["tool_input"]
    assert tool_input["test"] == "chi2-contingency"
    assert {k: float(tool_input[k]) for k in ("w", "alpha", "power", "df")} == {"w": 0.3, "alpha": 0.05, "power": 0.95, "df": 5.0}
    assert rec["tool_output"]["n_total"] == 220
    assert "220" in answer
