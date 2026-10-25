"""Agent tests with a scripted fake Claude and the real MCP server (no network)."""

import json
from datetime import datetime
from types import SimpleNamespace

import anyio
import pytest
from mcp import Client

from gpower_clone.agent import CallLogger, PowerAnalysisAgent, mcp_server_parameters
from gpower_clone.mcp_server import create_server

A_PRIORI_INPUT = {"test": "chi2-contingency", "mode": "a-priori", "w": 0.3, "alpha": 0.05, "power": 0.95, "df": 5}
LOG_KEYS = {"ts", "question", "tool_input", "tool_output", "tokens_in", "tokens_out"}


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(tool_input, block_id="toolu_1", name="power_analysis"):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def response(content, stop_reason, tokens_in=100, tokens_out=20):
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out),
    )


class FakeMessages:
    """Stands in for AsyncAnthropic().beta.messages. Each script step receives the message history."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.steps.pop(0)(kwargs["messages"])


def last_tool_results(messages):
    return [b for b in messages[-1]["content"] if b["type"] == "tool_result"]


def answer_from_tool_result(messages):
    """Final answer built only from the tool output, as the real agent is instructed to do."""
    result = json.loads(last_tool_results(messages)[0]["content"])
    if "error" in result:
        return response([text_block(f"Hata: {result['code']} ({result['field']})")], "end_turn", 300, 30)
    return response([text_block(f"Gerekli toplam örneklem: {result['n_total']}")], "end_turn", 300, 30)


def run_agent(fake, question, log_path, server=None):
    async def _run():
        async with Client(server or create_server()) as mcp_client:
            tools = (await mcp_client.list_tools()).tools
            agent = PowerAnalysisAgent(fake, mcp_client, tools, CallLogger(log_path))
            return await agent.ask(question)

    return anyio.run(_run)


def read_log(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_agent_calls_mcp_tool_and_logs(tmp_path):
    log_path = tmp_path / "logs" / "agent_calls.jsonl"
    question = "Kurgusal bir çalışmada w=0.3, alfa 0.05, güç 0.95 ve df=5 için kaç katılımcı gerekir?"
    fake = FakeMessages([
        lambda m: response([text_block("Hesaplıyorum."), tool_use_block(A_PRIORI_INPUT)], "tool_use", 120, 40),
        answer_from_tool_result,
    ])

    answer = run_agent(fake, question, log_path)

    assert answer == "Gerekli toplam örneklem: 220"
    records = read_log(log_path)
    assert len(records) == 1
    rec = records[0]
    assert set(rec) == LOG_KEYS
    assert rec["question"] == question
    assert rec["tool_input"] == A_PRIORI_INPUT
    assert rec["tool_output"]["n_total"] == 220
    assert abs(rec["tool_output"]["actual_power"] - 0.9502155) < 1e-6
    assert (rec["tokens_in"], rec["tokens_out"]) == (120, 40)
    assert datetime.fromisoformat(rec["ts"]).tzinfo is not None


def test_agent_sends_only_mcp_tool_to_claude(tmp_path):
    fake = FakeMessages([lambda m: response([text_block("Hangi df değerini kullanalım?")], "end_turn")])
    run_agent(fake, "w=0.3 için güç analizi yap", tmp_path / "log.jsonl")
    tools = fake.calls[0]["tools"]
    assert [t["name"] for t in tools] == ["power_analysis"]
    assert tools[0]["input_schema"]["required"] == ["test", "mode"]
    assert "Türkçe" in fake.calls[0]["system"]


def test_agent_without_tool_call_writes_no_log(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeMessages([lambda m: response([text_block("Lütfen alfa değerini belirtin.")], "end_turn")])
    answer = run_agent(fake, "Örneklem büyüklüğü hesapla", log_path)
    assert answer == "Lütfen alfa değerini belirtin."
    assert not log_path.exists()


@pytest.mark.parametrize(
    "tool_input,code,field",
    [
        ({k: v for k, v in A_PRIORI_INPUT.items() if k != "df"}, "MISSING_PARAM", "df"),
        ({**A_PRIORI_INPUT, "tails": 2}, "UNKNOWN_PARAM", "tails"),
        ({**A_PRIORI_INPUT, "df": 2.5}, "INVALID_VALUE", "df"),
        ({**A_PRIORI_INPUT, "alpha": 1.5}, "OUT_OF_RANGE", "alpha"),
    ],
    ids=["missing", "unknown", "invalid", "out-of-range"],
)
def test_agent_logs_tool_errors(tmp_path, tool_input, code, field):
    log_path = tmp_path / "log.jsonl"
    seen = {}

    def final(messages):
        seen["result"] = last_tool_results(messages)[0]
        return answer_from_tool_result(messages)

    fake = FakeMessages([lambda m: response([tool_use_block(tool_input)], "tool_use"), final])
    answer = run_agent(fake, "Kurgusal senaryo: hatalı giriş", log_path)

    assert seen["result"]["is_error"] is True
    assert answer == f"Hata: {code} ({field})"
    rec = read_log(log_path)[0]
    assert rec["tool_input"] == tool_input
    assert rec["tool_output"]["code"] == code
    assert rec["tool_output"]["field"] == field


def test_agent_logs_each_parallel_call_once(tmp_path):
    log_path = tmp_path / "log.jsonl"
    post_hoc = {"test": "chi2-contingency", "mode": "post-hoc", "w": 0.3, "alpha": 0.05, "n_total": 100, "df": 5}
    fake = FakeMessages([
        lambda m: response(
            [tool_use_block(A_PRIORI_INPUT, "toolu_a"), tool_use_block(post_hoc, "toolu_b")], "tool_use", 150, 60
        ),
        lambda m: response([text_block(f"{len(last_tool_results(m))} sonuç alındı")], "end_turn"),
    ])
    answer = run_agent(fake, "İki analiz", log_path)
    assert answer == "2 sonuç alındı"
    records = read_log(log_path)
    assert [r["tool_input"]["mode"] for r in records] == ["a-priori", "post-hoc"]
    assert abs(records[1]["tool_output"]["power"] - 0.6235846) < 1e-6
    # Usage is attributed once per model response
    assert [(r["tokens_in"], r["tokens_out"]) for r in records] == [(150, 60), (0, 0)]


def test_agent_rejects_unknown_tool_name(tmp_path):
    log_path = tmp_path / "log.jsonl"
    fake = FakeMessages([
        lambda m: response([tool_use_block(A_PRIORI_INPUT, name="calculator")], "tool_use"),
        lambda m: response([text_block("ok")], "end_turn"),
    ])
    run_agent(fake, "soru", log_path)
    rec = read_log(log_path)[0]
    assert rec["tool_output"]["code"] == "UNSUPPORTED"


def test_agent_over_stdio_subprocess(tmp_path):
    """Smoke test: same flow with the MCP server launched as a real stdio subprocess."""
    log_path = tmp_path / "log.jsonl"
    fake = FakeMessages([
        lambda m: response([tool_use_block(A_PRIORI_INPUT)], "tool_use"),
        answer_from_tool_result,
    ])
    answer = run_agent(fake, "stdio testi", log_path, server=mcp_server_parameters())
    assert answer == "Gerekli toplam örneklem: 220"
    assert read_log(log_path)[0]["tool_output"]["n_total"] == 220
